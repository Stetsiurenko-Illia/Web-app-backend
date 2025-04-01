import os
from django.core.asgi import get_asgi_application
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Встановлюємо DJANGO_SETTINGS_MODULE і ініціалізуємо налаштування
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo_project.settings')
django_asgi_app = get_asgi_application()

# Імпортуємо після ініціалізації налаштувань
import api.routing
from api.middleware import JWTAuthMiddleware

# Розділяємо маршрути для різних типів автентифікації
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": ProtocolTypeRouter({
        # Для /ws/tasks/ використовуємо JWTAuthMiddleware
        "tasks": JWTAuthMiddleware(
            URLRouter([
                path('ws/tasks/', api.routing.websocket_urlpatterns[0]),
            ])
        ),
        # Для /ws/online-users/ використовуємо AuthMiddlewareStack (сесійна автентифікація)
        "online-users": AuthMiddlewareStack(
            URLRouter([
                path('ws/online-users/', api.routing.websocket_urlpatterns[1]),
            ])
        ),
    }),
}) 