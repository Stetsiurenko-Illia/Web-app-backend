import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Task, CustomUser

logger = logging.getLogger(__name__)

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        logger.info(f"Connecting user: {self.user}, authenticated: {self.user is not None and self.user.is_authenticated}")
        if self.user is not None and self.user.is_authenticated:
            self.group_name = 'tasks'
            logger.info(f"Adding to group: {self.group_name}, channel: {self.channel_name}")
            try:
                await self.set_user_online()
                await self.channel_layer.group_add(self.group_name, self.channel_name)
                await self.accept()
                await self.update_online_users()
            except Exception as e:
                logger.error(f"Error in connect: {str(e)}")
                await self.close(code=1011)
        else:
            logger.warning("User not authenticated, closing connection")
            await self.close(code=1008)

    async def disconnect(self, close_code):
        if self.user is not None and self.user.is_authenticated:
            logger.info(f"Disconnecting user: {self.user}, close code: {close_code}")
            try:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                await self.set_user_offline()
                await self.update_online_users()
            except Exception as e:
                logger.error(f"Error in disconnect: {str(e)}")
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

            elif action == 'share_task':
                task_id = text_data_json.get('task_id')
                email = text_data_json.get('email')
                logger.info(f"Sharing task: task_id={task_id}, email={email}")

                if not task_id or not email:
                    logger.warning("Task ID or email is missing")
                    await self.send(text_data=json.dumps({
                        'error': 'Task ID and email are required'
                    }))
                    return

                # Перевіряємо, чи існує завдання і чи належить воно користувачу
                task = await self.get_task(task_id)
                if not task:
                    logger.warning(f"Task {task_id} not found")
                    await self.send(text_data=json.dumps({
                        'error': 'Task not found'
                    }))
                    return

                if task.user != self.user:
                    logger.warning(f"User {self.user.email} is not the owner of task {task_id}")
                    await self.send(text_data=json.dumps({
                        'error': 'You can only share your own tasks'
                    }))
                    return

                # Перевіряємо, чи існує користувач із вказаним email
                target_user = await self.get_user_by_email(email)
                if not target_user:
                    logger.warning(f"User with email {email} not found")
                    await self.send(text_data=json.dumps({
                        'error': 'User not found'
                    }))
                    return

                if target_user == self.user:
                    logger.warning(f"User {self.user.email} tried to share task with themselves")
                    await self.send(text_data=json.dumps({
                        'error': 'You cannot share a task with yourself'
                    }))
                    return

                # Додаємо завдання до shared_with
                await self.share_task_with_user(task, target_user)
                logger.info(f"Task {task_id} shared with {email}")

                # Надсилаємо повідомлення групі про поширення завдання
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'task_message',
                        'action': 'share_task',
                        'task': {
                            'id': task.id,
                            'title': task.title,
                            'description': task.description,
                            'completed': task.completed,
                            'user': self.user.email,
                            'shared_with': email,
                        }
                    }
                )
                logger.info("Share task message sent to group")

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': f'Error processing request: {str(e)}'
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
    def set_user_online(self):
        try:
            self.user.is_online = True
            self.user.save()
            logger.info(f"User {self.user.email} set to online")
        except Exception as e:
            logger.error(f"Error setting user online: {str(e)}")
            raise

    @database_sync_to_async
    def set_user_offline(self):
        try:
            self.user.is_online = False
            self.user.save()
            logger.info(f"User {self.user.email} set to offline")
        except Exception as e:
            logger.error(f"Error setting user offline: {str(e)}")
            raise

    @database_sync_to_async
    def get_online_users(self):
        try:
            online_users = list(CustomUser.objects.filter(is_online=True).values_list('email', flat=True))
            logger.info(f"Online users retrieved: {online_users}")
            return online_users
        except Exception as e:
            logger.error(f"Error getting online users: {str(e)}")
            return []

    async def update_online_users(self):
        try:
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
            logger.info("Online users message sent to admin_online group")
        except Exception as e:
            logger.error(f"Error in update_online_users: {str(e)}")
            raise

    @database_sync_to_async
    def get_task(self, task_id):
        try:
            return Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user_by_email(self, email):
        try:
            return CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return None

    @database_sync_to_async
    def share_task_with_user(self, task, target_user):
        try:
            task.shared_with.add(target_user)
            task.save()
            logger.info(f"Task {task.id} shared with {target_user.email}")
        except Exception as e:
            logger.error(f"Error sharing task: {str(e)}")
            raise
class OnlineUsersConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        logger.info(f"Connecting admin user: {self.user}, is_staff: {self.user.is_staff if self.user else False}")
        if self.user and self.user.is_authenticated and self.user.is_staff:
            await self.channel_layer.group_add('admin_online', self.channel_name)
            await self.accept()
            logger.info(f"Admin {self.user.email} connected to admin_online group")
        else:
            logger.warning("User not admin or not authenticated, closing connection")
            await self.close(code=1008)

    async def disconnect(self, close_code):
        if self.user and self.user.is_authenticated and self.user.is_staff:
            logger.info(f"Disconnecting admin user: {self.user}, close code: {close_code}")
            await self.channel_layer.group_discard('admin_online', self.channel_name)

    async def online_users_message(self, event):
        logger.info(f"Sending online users to admin: {event['users']}")
        await self.send(text_data=json.dumps({
            'action': event['action'],
            'users': event['users'],
        }))