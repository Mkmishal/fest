from django.urls import re_path
from .consumers import OnlineUsersConsumer

websocket_urlpatterns = [
    re_path(r'ws/online-users/$', OnlineUsersConsumer.as_asgi()),
]
