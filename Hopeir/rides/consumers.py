import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.timezone import now
from .models import Rides, RideRequest
from asgiref.sync import sync_to_async

class RideActionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'ride_{self.ride_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

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
        await sync_to_async(RideRequest.objects.filter(ride=ride, status='pending').update)(status='rejected')

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
        
