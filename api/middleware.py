import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        # Перевіряємо токен
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        user = User.objects.get(id=user_id)
        return user
    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        print(f"Token validation error: {str(e)}")  # Додаємо логування
        return None

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Отримуємо query_string із scope
        query_string = scope.get('query_string', b'').decode()
        token = None

        # Парсимо query_string, щоб знайти token
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break

        if token:
            # Отримуємо користувача за токеном
            user = await get_user_from_token(token)
            if user:
                scope['user'] = user
                print(f"User authenticated: {user.email}")  # Додаємо логування
            else:
                scope['user'] = None
                print("User not authenticated: Invalid token")  # Додаємо логування
        else:
            scope['user'] = None
            print("User not authenticated: No token provided")  # Додаємо логування

        return await self.app(scope, receive, send)