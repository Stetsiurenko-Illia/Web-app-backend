import os
from django.core.asgi import get_asgi_application
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from api.middleware import JWTAuthMiddleware
import api.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo_project.settings')
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": ProtocolTypeRouter({
        # Для /ws/tasks/ використовуємо JWTAuthMiddleware
        "tasks": JWTAuthMiddleware(
            URLRouter([
                path('ws/tasks/', api.routing.websocket_urlpatterns[0]),
            ])
        ),
        # Для /ws/online-users/ використовуємо AuthMiddlewareStack
        "online-users": AuthMiddlewareStack(
            URLRouter([
                path('ws/online-users/', api.routing.websocket_urlpatterns[1]),
            ])
        ),
    }),
})