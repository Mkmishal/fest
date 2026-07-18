"""
ASGI config for housing project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from channels.routing import get_default_application
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import controller.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'housing.settings')

application = get_asgi_application()
django.setup()
application = get_default_application()




application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            controller.routing.websocket_urlpatterns
        )
    ),
})