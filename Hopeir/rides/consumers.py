from email.mime import message
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.timezone import now

from Hopeir.core.models import CustomUser
from .models import Rides, RideRequest, RideChatMessage
from asgiref.sync import sync_to_async
from urllib.parse import parse_qs
from datetime import datetime
from channels.db import database_sync_to_async

class RideActionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'ride_{self.ride_id}'

        query_string = self.scope["query_string"].decode()
        self.user_id = parse_qs(query_string).get("user_id", [None])[0]

        if not self.user_id:
            await self.close()
            return

        # ✅ Fetch ride AND driver in one DB hit
        ride = await sync_to_async(
            Rides.objects.select_related("user").get
        )(id=self.ride_id)

        # ✅ Safe: user is already loaded, no extra DB call
        is_driver = str(ride.user.user_id) == str(self.user_id)

        # ✅ Check accepted passenger safely
        is_accepted = await sync_to_async(
            RideRequest.objects.filter(
                ride=ride,
                from_user__user_id=self.user_id,
                request_status="accepted"
            ).exists
        )()

        if not (is_driver or is_accepted):
            await self.close()
            return

        self.is_driver = is_driver

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # ✅ Frontend contract unchanged
        await self.send(text_data=json.dumps({
            "status": ride.status,
            "message": f"Connected to ride {self.ride_id}. Current status: {ride.status}"
        }))


    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        ride = await sync_to_async(Rides.objects.get)(id=self.ride_id)

        # ---------- EXISTING RIDE ACTIONS (UNCHANGED OUTPUT) ----------
        if action in ['start', 'end', 'cancel']:

            if not self.is_driver:
                return  # silent ignore, frontend-safe

            if ride.status in ['completed', 'cancelled']:
                await self.send(text_data=json.dumps({
                    'error': f'Ride is already {ride.status}'
                }))
                return

            if action == 'start':
                if ride.status != 'pending':
                    return
                ride.status = 'ongoing'
                ride.start_time = now()

            elif action == 'end':
                if ride.status != 'ongoing':
                    await self.send(text_data=json.dumps({
                        'error': 'Cannot end ride unless it is ongoing'
                    }))
                    return
                ride.status = 'completed'
                ride.end_time = now()

            elif action == 'cancel':
                ride.status = 'cancelled'

            await sync_to_async(ride.save)()

            await sync_to_async(
                RideRequest.objects.filter(
                    ride=ride,
                    request_status='pending'
                ).update
            )(request_status='rejected')

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'ride_status_update',
                    'status': ride.status,
                    'message': f'Ride {action}ed successfully'
                }
            )
            return

        # ---------- NEW: CHAT MESSAGE ---------
        if action == "chat":
            message = data.get("message")
            if not message:
                return

        sender = await sync_to_async(CustomUser.objects.get)(user_id=self.user_id)

        chat = await sync_to_async(RideChatMessage.objects.create)(
            ride=ride,
            sender=sender,
            message=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": chat.message,
                "sender": {
                    "id": sender.user_id,
                    "name": sender.first_name,
                },
                "timestamp": chat.created_at.isoformat()
            }
        )

        # ---------- NEW: DRIVER LOCATION ----------
        if action == 'location_update':
            if not self.is_driver:
                return

            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if latitude is None or longitude is None:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'driver_location',
                    'latitude': latitude,
                    'longitude': longitude
                }
            )
            return

    async def ride_status_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'timestamp': event['timestamp']
        }))

    async def driver_location(self, event):
        await self.send(text_data=json.dumps({
            'type': 'driver_location',
            'latitude': event['latitude'],
            'longitude': event['longitude']
        }))

        

class RideRequestConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        query_string = self.scope["query_string"].decode()
        user_id = parse_qs(query_string).get("user_id", [None])[0]

        if not user_id:
            await self.close()
            return

        self.user_id = user_id
        self.group_name = f"user_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        requests = await self.get_relevant_requests(self.user_id)

        await self.send(text_data=json.dumps({
            "type": "initial_state",
            "data": requests
        }))

    @database_sync_to_async
    def process_request_action(self, request_id, action):
        from django.db import transaction

        with transaction.atomic():
            req = RideRequest.objects.select_for_update().select_related(
                "ride", "from_user", "ride__user"
            ).get(id=request_id)

            ride = req.ride

            if ride.status in ["ongoing", "completed", "cancelled"]:
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

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        request_id = data.get("request_id")

        if action not in ["accept", "reject"] or not request_id:
            await self.send(json.dumps({
                "type": "error",
                "message": "Invalid action or request_id"
            }))
            return

        try:
            ride_request = await self.process_request_action(request_id, action)
        except ValueError as e:
            await self.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))
            return

        response_data = {
            "id": ride_request.id,
            "ride_id": ride_request.ride.id,
            "request_status": ride_request.request_status,
            "passenger_id": ride_request.from_user.user_id,
        }

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

    async def ride_request_updated(self, event):
        await self.send(text_data=json.dumps({
            "type": "ride_request_updated",
            "data": event["data"]
        }))
