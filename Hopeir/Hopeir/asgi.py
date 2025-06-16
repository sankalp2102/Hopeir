"""
ASGI config for Hopeir project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hopeir.settings')
django.setup()


from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from rides.routing import websocket_urlpatterns





application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
