"""
ASGI config for wireguard project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from django.urls import path, re_path
from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
import django_eventstream
from .middlewares import TokenAuthMiddleware, TokenAuthMiddlewareStack 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wireguard.settings')

# application = get_asgi_application()

# application = ProtocolTypeRouter({
#     'http': URLRouter([
#         path('events/', AuthMiddlewareStack(
#             URLRouter(django_eventstream.routing.urlpatterns)
#         ), { 'channels': ['test'] }),
#         re_path(r'', get_asgi_application()),
#     ]),
# })


application = ProtocolTypeRouter({
    'http': URLRouter([
        path('events/data-monitor/', TokenAuthMiddleware(
            URLRouter(django_eventstream.routing.urlpatterns)
        ), { 'channels': ['monitor'] }),
        re_path(r'', get_asgi_application()),
    ]),
})
