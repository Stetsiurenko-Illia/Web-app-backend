import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Task, CustomUser

logger = logging.getLogger(__name__)

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_authenticated:
            self.group_name = 'tasks'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            await self.update_online_users()

            import asyncio
            while True:
                await asyncio.sleep(30)
                await self.send(text_data=json.dumps({'action': 'heartbeat'}))
        else:
            logger.warning("User not authenticated, closing connection")
            await self.close()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            logger.info(f"Disconnecting user: {self.user}, close code: {close_code}")
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.update_online_users()
        else:
            logger.warning("Disconnecting unauthenticated user")

    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            logger.info(f"Action: {action}")

            if action == 'create_task':
                title = text_data_json.get('title')
                description = text_data_json.get('description', '')
                completed = text_data_json.get('completed', False)
                logger.info(f"Creating task: title={title}, description={description}, completed={completed}")

                if not title:
                    logger.warning("Title is empty")
                    await self.send(text_data=json.dumps({
                        'error': 'Title is required'
                    }))
                    return

                task = await self.create_task(title, description, completed)
                logger.info(f"Task created: {task.id}")

                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'task_message',
                        'action': 'create_task',
                        'task': {
                            'id': task.id,
                            'title': task.title,
                            'description': task.description,
                            'completed': task.completed,
                            'user': self.user.email,
                        }
                    }
                )
                logger.info("Task message sent to group")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': f'Error creating task: {str(e)}'
            }))

    async def task_message(self, event):
        logger.info(f"Sending task message to client: {event}")
        await self.send(text_data=json.dumps({
            'action': event['action'],
            'task': event['task'],
        }))

    @database_sync_to_async
    def create_task(self, title, description, completed):
        try:
            task = Task.objects.create(
                user=self.user,
                title=title,
                description=description,
                completed=completed
            )
            logger.info(f"Task created in DB: {task.id}")
            return task
        except Exception as e:
            logger.error(f"Error creating task in DB: {str(e)}")
            raise

    @database_sync_to_async
    def get_online_users(self):
        return list(CustomUser.objects.filter(is_online=True).values_list('email', flat=True))

    async def update_online_users(self):
        online_users = await self.get_online_users()
        logger.info(f"Updating online users: {online_users}")
        await self.channel_layer.group_send(
            'admin_online',
            {
                'type': 'online_users_message',
                'action': 'online_users',
                'users': online_users,
            }
        )

class OnlineUsersConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        logger.info(f"Connecting admin user: {self.user}, is_staff: {self.user.is_staff}")
        if self.user.is_authenticated and self.user.is_staff:
            await self.channel_layer.group_add('admin_online', self.channel_name)
            await self.accept()
        else:
            logger.warning("User not admin, closing connection")
            await self.close()

    async def disconnect(self, close_code):
        if self.user.is_authenticated and self.user.is_staff:
            logger.info(f"Disconnecting admin user: {self.user}, close code: {close_code}")
            await self.channel_layer.group_discard('admin_online', self.channel_name)

    async def online_users_message(self, event):
        logger.info(f"Sending online users to admin: {event['users']}")
        await self.send(text_data=json.dumps({
            'action': event['action'],
            'users': event['users'],
        }))