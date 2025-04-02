import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.auth import AuthMiddlewareStack
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        user = User.objects.get(id=user_id)
        return user
    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        print(f"Token validation error: {str(e)}")
        return None

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        token = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break

        if token:
            user = await get_user_from_token(token)
            if user:
                scope['user'] = user
                print(f"User authenticated: {user.email}")
            else:
                scope['user'] = None
                print("User not authenticated: Invalid token")
        else:
            scope['user'] = None
            print("User not authenticated: No token provided")

        return await self.inner(scope, receive, send)

class SelectiveAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        self.inner = inner
        self.jwt_middleware = JWTAuthMiddleware(inner)
        self.session_middleware = AuthMiddlewareStack(inner)

    async def __call__(self, scope, receive, send):
        path = scope['path']
        if path.startswith('/ws/tasks/'):
            # Для /ws/tasks/ використовуємо JWTAuthMiddleware
            return await self.jwt_middleware(scope, receive, send)
        elif path.startswith('/ws/online-users/'):
            # Для /ws/online-users/ використовуємо AuthMiddlewareStack
            return await self.session_middleware(scope, receive, send)
        else:
            # За замовчуванням використовуємо сесійну автентифікацію
            return await self.session_middleware(scope, receive, send)