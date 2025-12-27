import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.timezone import now
from .models import Rides, RideRequest, RideChatMessage, CustomUser
from asgiref.sync import sync_to_async
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

        try:
            self.ride = await sync_to_async(
                Rides.objects.select_related("user").get
            )(id=self.ride_id)
        except Rides.DoesNotExist:
            await self.close()
            return

        self.is_driver = str(self.ride.user.user_id) == str(self.user_id)

        self.is_accepted_passenger = await sync_to_async(
            RideRequest.objects.filter(
                ride=self.ride,
                from_user__user_id=self.user_id,
                request_status="accepted",
            ).exists
        )()

        if not (self.is_driver or self.is_accepted_passenger):
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        # 🔹 EXISTING CONNECTION PAYLOAD
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

        # =====================================================
        # SEND CHAT HISTORY ON CONNECT
        # =====================================================

        chat_history = await sync_to_async(list)(
            RideChatMessage.objects.filter(ride=self.ride)
            .select_related("sender")
            .order_by("created_at")
            .values(
                "id",
                "message",
                "created_at",
                "sender__user_id",
            )
        )

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
                            "sender_id": chat["sender__user_id"],
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

        return

    # ===================== CHAT =====================

    async def _handle_chat(self, data):
        message = data.get("message")
        if not message:
            return

        try:
            sender = await sync_to_async(CustomUser.objects.get)(
                user_id=self.user_id
            )
        except CustomUser.DoesNotExist:
            return

        chat = await sync_to_async(RideChatMessage.objects.create)(
            ride=self.ride,
            sender=sender,
            message=message,
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": chat.message,
                "sender_id": sender.user_id,
                "timestamp": chat.created_at.isoformat(),
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

        if self.ride.status in {"completed", "cancelled"}:
            return

        if action == "start" and self.ride.status == "pending":
            self.ride.status = "ongoing"
            self.ride.start_time = now()

        elif action == "end" and self.ride.status == "ongoing":
            self.ride.status = "completed"
            self.ride.end_time = now()

        elif action == "cancel":
            self.ride.status = "cancelled"

        else:
            return

        await sync_to_async(self.ride.save)()

        await sync_to_async(
            RideRequest.objects.filter(
                ride=self.ride,
                request_status="pending",
            ).update
        )(request_status="rejected")

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



        
class RideRequestConsumer(AsyncWebsocketConsumer):
    """
    Handles real-time ride request lifecycle:
    - Initial request list on connect
    - Accept / Reject by driver
    - Real-time updates to driver & passenger
    """

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

        # Send initial state
        requests = await self.get_relevant_requests(self.user_id)

        await self.send(text_data=json.dumps({
            "type": "initial_state",
            "data": requests
        }))

    # ======================================================
    # RECEIVE (ROUTER)
    # ======================================================
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get("action")
        request_id = data.get("request_id")

        if action not in {"accept", "reject"} or not request_id:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Invalid action or request_id"
            }))
            return

        try:
            ride_request = await self.process_request_action(
                request_id=request_id,
                action=action,
                user_id=self.user_id
            )
        except ValueError as exc:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": str(exc)
            }))
            return

        response_data = self.serialize_request(ride_request)

        # Notify both driver and passenger
        driver_group = f"user_{ride_request.ride.user.user_id}"
        passenger_group = f"user_{ride_request.from_user.user_id}"

        for group in {driver_group, passenger_group}:
            await self.channel_layer.group_send(
                group,
                {
                    "type": "ride_request_updated",
                    "data": response_data
                }
            )

    # ======================================================
    # GROUP EVENT HANDLER
    # ======================================================
    async def ride_request_updated(self, event):
        await self.send(text_data=json.dumps({
            "type": "ride_request_updated",
            "data": event["data"]
        }))

    # ======================================================
    # DB HELPERS (SYNC → ASYNC SAFE)
    # ======================================================
    @database_sync_to_async
    def get_relevant_requests(self, user_id):
        """
        Fetch all ride requests relevant to the user.
        Driver → requests for their rides
        Passenger → requests they sent
        """
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

        # Convert datetime → JSON-safe string
        return [
            {
                **row,
                "requested_at": row["requested_at"].isoformat()
                if row["requested_at"] else None
            }
            for row in qs
        ]

    @database_sync_to_async
    def process_request_action(self, request_id, action, user_id):
        """
        Accept or reject a ride request.
        Only the driver of the ride can perform this action.
        """
        with transaction.atomic():
            try:
                # Lock ONLY the RideRequest row
                req = RideRequest.objects.select_for_update().get(id=request_id)
            except RideRequest.DoesNotExist:
                raise ValueError("Ride request no longer exists")

            ride = req.ride

            # Authorization
            if ride.user.user_id != user_id:
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
            return req

    # ======================================================
    # SERIALIZER (INTERNAL)
    # ======================================================
    def serialize_request(self, req):
        return {
            "id": req.id,
            "ride_id": req.ride.id,
            "request_status": req.request_status,
            "requested_at": req.requested_at.isoformat(),
            "passenger_id": req.from_user.user_id,
            "driver_id": req.ride.user.user_id,
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