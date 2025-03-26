import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Task, CustomUser


class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Додаємо користувача до групи "tasks"
        self.group_name = "tasks"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Видаляємо користувача з групи при відключенні
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Отримуємо повідомлення від клієнта
        text_data_json = json.loads(text_data)
        action = text_data_json.get("action")

        if action == "create_task":
            title = text_data_json["title"]
            description = text_data_json.get("description", "")
            completed = text_data_json.get("completed", False)
            user = self.scope["user"]

            # Створюємо задачу в базі
            task = await self.create_task(user, title, description, completed)

            # Відправляємо повідомлення всім у групі
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "task_update",
                    "task": {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "completed": task.completed,
                        "user": user.email,
                    }
                }
            )

    async def task_update(self, event):
        # Відправляємо оновлення задачі клієнту
        task = event["task"]
        await self.send(text_data=json.dumps({
            "action": "task_updated",
            "task": task
        }))

    @database_sync_to_async
    def create_task(self, user, title, description, completed):
        return Task.objects.create(
            user=user,
            title=title,
            description=description,
            completed=completed
        )


class OnlineUsersConsumer(AsyncWebsocketConsumer):
    online_users = set()  # Зберігаємо список онлайн-користувачів

    async def connect(self):
        user = self.scope["user"]
        if user.is_authenticated and user.is_staff:  # Тільки для адміністраторів
            self.online_users.add(user.email)
            await self.channel_layer.group_add("admin_online", self.channel_name)
            await self.accept()
            # Відправляємо список онлайн-користувачів
            await self.send_online_users()

    async def disconnect(self, close_code):
        user = self.scope["user"]
        if user.is_authenticated:
            self.online_users.discard(user.email)
            await self.channel_layer.group_discard("admin_online", self.channel_name)
            # Оновлюємо список для всіх адміністраторів
            await self.send_online_users()

    async def send_online_users(self):
        await self.channel_layer.group_send(
            "admin_online",
            {
                "type": "online_users_update",
                "users": list(self.online_users)
            }
        )

    async def online_users_update(self, event):
        await self.send(text_data=json.dumps({
            "action": "online_users",
            "users": event["users"]
        }))