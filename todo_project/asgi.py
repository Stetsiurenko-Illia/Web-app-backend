import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

# Встановлюємо DJANGO_SETTINGS_MODULE і ініціалізуємо налаштування
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo_project.settings')
django_asgi_app = get_asgi_application()

# Імпортуємо після ініціалізації налаштувань
import api.routing
from api.middleware import SelectiveAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": SelectiveAuthMiddleware(
        URLRouter(
            api.routing.websocket_urlpatterns
        )
    ),
})