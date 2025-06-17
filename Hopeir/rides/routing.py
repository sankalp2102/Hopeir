from django.urls import re_path
from .consumers import RideActionConsumer 
from . import consumers
websocket_urlpatterns = [
    re_path(r'ws/ride-requests/$', consumers.RideRequestConsumer.as_asgi()),
    re_path(r'ws/ride/(?P<ride_id>\d+)/$', RideActionConsumer.as_asgi()),
]