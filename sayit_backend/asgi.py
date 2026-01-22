import os 
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sayit_backend.settings")

django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from Chat.middleware import JwtAuthMiddleware


from Chat.routers import websocket_urlpatterns


application = ProtocolTypeRouter({
    'http' : get_asgi_application(),
    'websocket' : JwtAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    )
})