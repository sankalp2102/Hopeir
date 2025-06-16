from django.urls import re_path
from .consumers import RideActionConsumer

websocket_urlpatterns = [
    re_path(r'ws/ride/(?P<ride_id>\d+)/$', RideActionConsumer.as_asgi()),
]