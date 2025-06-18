from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def notify_user_about_request(user_id, request_data, notification_type):
    """
    Sends a message to a user's WebSocket group.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": f"ride_request_{notification_type}",  # example: ride_request_new_request or ride_request_request_updated
            "data": request_data
        }
    )

def notify_ride_update(ride_id, status, message):
    """
    Sends a ride status update to all users in the ride room group.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"ride_{ride_id}",
        {
            "type": "ride_status_update",
            "status": status,
            "message": message
        }
    )