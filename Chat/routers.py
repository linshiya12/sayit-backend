from django.urls import re_path
from .consumer import ChatConsumer,StatusConsumer,VideoConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>[\w_]+)/$', ChatConsumer.as_asgi()),
    re_path(r'ws/online/$', StatusConsumer.as_asgi()),
    re_path(r'ws/video/(?P<room_name>[\w_]+)/$', VideoConsumer.as_asgi()),
]
