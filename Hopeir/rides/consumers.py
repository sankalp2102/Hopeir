import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.timezone import now
from .models import Rides, RideRequest
from asgiref.sync import sync_to_async
from urllib.parse import parse_qs
from datetime import datetime
from channels.db import database_sync_to_async

class RideActionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'ride_{self.ride_id}'

        # Optional: extract user_id from query string if access control is needed
        query_string = self.scope["query_string"].decode()
        self.user_id = parse_qs(query_string).get("user_id", [None])[0]

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        ride = await sync_to_async(Rides.objects.get)(id=self.ride_id)

        # Optional: uncomment if access control is needed
        # has_access = await sync_to_async(RideRequest.objects.filter(
        #     ride=ride,
        #     from_user__user_id=self.user_id,
        #     request_status='accepted'
        # ).exists)()
        # if not has_access:
        #     await self.send(text_data=json.dumps({
        #         'error': 'Access denied. Only accepted users can control this ride.'
        #     }))
        #     return

        await self.send(text_data=json.dumps({
            'status': ride.status,
            'message': f'Connected to ride {self.ride_id}. Current status: {ride.status}'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        ride = await sync_to_async(Rides.objects.get)(id=self.ride_id)

        if ride.status in ['completed', 'cancelled']:
            await self.send(text_data=json.dumps({
                'error': f'Ride is already {ride.status}'
            }))
            return

        if action == 'start':
            ride.status = 'ongoing'
            ride.start_time = now()
        elif action == 'end':
            if ride.status != 'ongoing':
                await self.send(text_data=json.dumps({'error': 'Cannot end ride unless it is ongoing'}))
                return
            ride.status = 'completed'
            ride.end_time = now()
        elif action == 'cancel':
            ride.status = 'cancelled'
        else:
            await self.send(text_data=json.dumps({'error': 'Invalid action'}))
            return

        await sync_to_async(ride.save)()

        # Reject all remaining pending requests
        await sync_to_async(
            RideRequest.objects.filter(ride=ride, request_status='pending').update
        )(request_status='rejected')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'ride_status_update',
                'status': ride.status,
                'message': f'Ride {action}ed successfully'
            }
        )

    async def ride_status_update(self, event):
        await self.send(text_data=json.dumps({
            'status': event['status'],
            'message': event['message']
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
