import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.timezone import now
from .models import Rides, RideRequest, RideChatMessage, CustomUser
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.db.models import Q
from django.db import transaction


class RideActionConsumer(AsyncWebsocketConsumer):
    # ===================== CONNECTION =====================

    async def connect(self):
        self.ride_id = self.scope["url_route"]["kwargs"].get("ride_id")
        self.room_group_name = f"ride_{self.ride_id}"

        query_string = self.scope.get("query_string", b"").decode()
        self.user_id = parse_qs(query_string).get("user_id", [None])[0]

        if not self.user_id or not self.ride_id:
            await self.close()
            return

        self.ride = await self._get_ride(self.ride_id)
        if self.ride is None:
            await self.close()
            return

        self.is_driver = str(self.ride.user.user_id) == str(self.user_id)

        self.is_accepted_passenger = await self._check_accepted_passenger(
            self.ride, self.user_id
        )

        if not (self.is_driver or self.is_accepted_passenger):
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection",
                    "ride_id": self.ride_id,
                    "status": self.ride.status,
                    "role": "driver" if self.is_driver else "passenger",
                }
            )
        )

        chat_history = await self._get_chat_history(self.ride)

        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_history",
                    "ride_id": self.ride_id,
                    "messages": [
                        {
                            "id": chat["id"],
                            "message": chat["message"],
                            "timestamp": chat["created_at"].isoformat(),
                            "sender_id": str(chat["sender__user_id"]),
                        }
                        for chat in chat_history
                    ],
                }
            )
        )

    # ===================== RECEIVE ROUTER =====================

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get("action")

        if action == "chat":
            await self._handle_chat(data)
            return

        if action in {"start", "end", "cancel"}:
            await self._handle_ride_action(action)
            return

        if action == "location_update":
            await self._handle_location_update(data)
            return

    # ===================== CHAT =====================

    async def _handle_chat(self, data):
        message = data.get("message")
        if not message:
            return

        result = await self._save_chat_message(self.ride, self.user_id, message)
        if result is None:
            return

        chat_msg, sender_id = result

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": chat_msg.message,
                "sender_id": str(sender_id),
                "timestamp": chat_msg.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "message": event["message"],
                    "sender_id": event["sender_id"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    # ===================== RIDE ACTIONS =====================

    async def _handle_ride_action(self, action):
        if not self.is_driver:
            return

        fresh_status = await self._get_ride_status(self.ride_id)
        if fresh_status is None:
            return

        if fresh_status in {"completed", "cancelled"}:
            return

        if action == "start" and fresh_status == "pending":
            self.ride.status = "ongoing"
            self.ride.start_time = now()

        elif action == "end" and fresh_status == "ongoing":
            self.ride.status = "completed"
            self.ride.end_time = now()

        elif action == "cancel":
            self.ride.status = "cancelled"

        else:
            return

        await self._save_ride_and_reject_pending(self.ride)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "ride_status_update",
                "status": self.ride.status,
            },
        )

    async def ride_status_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "ride_status_update",
                    "status": event["status"],
                }
            )
        )

    # ===================== DRIVER LOCATION =====================

    async def _handle_location_update(self, data):
        if not self.is_driver:
            return

        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if latitude is None or longitude is None:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "driver_location",
                "latitude": latitude,
                "longitude": longitude,
            },
        )

    async def driver_location(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "driver_location",
                    "latitude": event["latitude"],
                    "longitude": event["longitude"],
                }
            )
        )

    # ===================== DISCONNECT =====================

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    # ===================== DB HELPERS =====================

    @database_sync_to_async
    def _get_ride(self, ride_id):
        try:
            return Rides.objects.select_related("user").get(id=ride_id)
        except Rides.DoesNotExist:
            return None

    @database_sync_to_async
    def _check_accepted_passenger(self, ride, user_id):
        return RideRequest.objects.filter(
            ride=ride,
            from_user__user_id=user_id,
            request_status="accepted",
        ).exists()

    @database_sync_to_async
    def _get_chat_history(self, ride):
        return list(
            RideChatMessage.objects.filter(ride=ride)
            .select_related("sender")
            .order_by("created_at")
            .values("id", "message", "created_at", "sender__user_id")
        )

    @database_sync_to_async
    def _save_chat_message(self, ride, user_id, message):
        try:
            sender = CustomUser.objects.get(user_id=user_id)
        except CustomUser.DoesNotExist:
            return None
        chat = RideChatMessage.objects.create(
            ride=ride, sender=sender, message=message
        )
        return chat, sender.user_id

    @database_sync_to_async
    def _get_ride_status(self, ride_id):
        try:
            return Rides.objects.values_list("status", flat=True).get(id=ride_id)
        except Rides.DoesNotExist:
            return None

    @database_sync_to_async
    def _save_ride_and_reject_pending(self, ride):
        ride.save()
        RideRequest.objects.filter(
            ride=ride,
            request_status="pending",
        ).update(request_status="rejected")


# ══════════════════════════════════════════════════════════════════════════


class RideRequestConsumer(AsyncWebsocketConsumer):

    # ======================================================
    # CONNECT
    # ======================================================
    async def connect(self):
        query_string = self.scope.get("query_string", b"").decode()
        self.user_id = parse_qs(query_string).get("user_id", [None])[0]

        if not self.user_id:
            await self.close(code=4001)
            return

        self.group_name = f"user_{self.user_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        try:
            requests = await self.get_relevant_requests(self.user_id)
            await self.send(text_data=json.dumps({
                "type": "initial_state",
                "data": requests
            }))
        except Exception as e:
            # FIX 2: UUID serialization error on connect must not kill connection
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"Failed to load initial requests: {str(e)}"
            }))

    # ======================================================
    # RECEIVE (ROUTER)
    # ======================================================
    async def receive(self, text_data):
        # FIX 1: wrap entire receive in try/except
        # Any unhandled exception previously bubbled up to Channels
        # which closed the WebSocket — now we catch everything,
        # send an error message back, and keep the connection alive
        try:
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
                return

            action = data.get("action")
            request_id = data.get("request_id")

            if action not in {"accept", "reject"} or not request_id:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid action or missing request_id"
                }))
                return

            response_data = await self.process_request_action(
                request_id=request_id,
                action=action,
                user_id=self.user_id
            )

            driver_group    = f"user_{response_data['driver_id']}"
            passenger_group = f"user_{response_data['passenger_id']}"

            # FIX 4: list instead of set — deterministic order
            groups = list({driver_group, passenger_group})
            for group in groups:
                await self.channel_layer.group_send(
                    group,
                    {
                        "type": "ride_request_updated",
                        "data": response_data
                    }
                )

        except ValueError as exc:
            # Business logic errors — send message, keep connection alive
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": str(exc)
            }))

        except Exception as exc:
            # FIX 1: catch ALL other exceptions — DB errors, integrity errors etc.
            # Send error to client, connection stays open
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Something went wrong, please try again"
            }))

    # ======================================================
    # GROUP EVENT HANDLER
    # ======================================================
    async def ride_request_updated(self, event):
        await self.send(text_data=json.dumps({
            "type": "ride_request_updated",
            "data": event["data"]
        }))

    # ======================================================
    # DB HELPERS
    # ======================================================
    @database_sync_to_async
    def get_relevant_requests(self, user_id):
        qs = (
            RideRequest.objects
            .select_related("ride", "from_user", "ride__user")
            .filter(
                Q(ride__user__user_id=user_id) |
                Q(from_user__user_id=user_id)
            )
            .order_by("-requested_at")
            .values(
                "id",
                "ride_id",
                "request_status",
                "requested_at",
                "from_user__user_id",
                "from_user__first_name",
                "ride__user__user_id",
            )
        )

        # FIX 2: cast UUID fields to str so json.dumps never fails
        # uuid.UUID objects are not JSON serializable — this was
        # silently crashing on connect and disconnecting the socket
        return [
            {
                "id": row["id"],
                "ride_id": row["ride_id"],
                "request_status": row["request_status"],
                "requested_at": row["requested_at"].isoformat() if row["requested_at"] else None,
                "from_user_id": str(row["from_user__user_id"]) if row["from_user__user_id"] else None,
                "from_user_name": row["from_user__first_name"] or "",
                "driver_id": str(row["ride__user__user_id"]) if row["ride__user__user_id"] else None,
            }
            for row in qs
        ]

    @database_sync_to_async
    def process_request_action(self, request_id, action, user_id):
        with transaction.atomic():
            try:
                req = (
                    RideRequest.objects
                    .select_for_update()
                    .select_related("ride__user", "from_user")
                    .get(id=request_id)
                )
            except RideRequest.DoesNotExist:
                raise ValueError("Ride request no longer exists")

            ride = req.ride

            if str(ride.user.user_id) != str(user_id):
                raise ValueError("Only the driver can process this request")

            if ride.status in {"ongoing", "completed", "cancelled"}:
                raise ValueError("Ride is no longer accepting requests")

            if req.request_status != "pending":
                raise ValueError("Request already processed")

            if action == "accept":
                if ride.seats <= 0:
                    raise ValueError("No seats available")

                req.request_status = "accepted"
                ride.seats -= 1
                ride.save()

                if ride.seats == 0:
                    RideRequest.objects.filter(
                        ride=ride,
                        request_status="pending"
                    ).update(request_status="rejected")

            elif action == "reject":
                req.request_status = "rejected"
            else:
                raise ValueError("Invalid action")

            req.save()

            # All fields from select_related — zero extra queries
            # Cast UUIDs to str here so the dict is JSON serializable
            return {
                "id": req.id,
                "ride_id": ride.id,
                "request_status": req.request_status,
                "requested_at": req.requested_at.isoformat(),
                "passenger_id": str(req.from_user.user_id),
                "driver_id": str(ride.user.user_id),
            }

    # ======================================================
    # DISCONNECT
    # ======================================================
    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )