import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack


# Встановлюємо DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo_project.settings')

# Ініціалізуємо Django ASGI додаток
django_asgi_app = get_asgi_application()

import api.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
           api.routing.websocket_urlpatterns
        )
    ),
})