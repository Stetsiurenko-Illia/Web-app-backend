from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import CustomUser, Task
import time
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime


@shared_task(queue='email')
def send_email_to_online_users(subject, message):
    online_users = CustomUser.objects.filter(is_online=True)
    recipient_emails = [user.email for user in online_users if user.email]
    if recipient_emails:
        send_mail(
            subject,
            message,
            'your_email@gmail.com',
            recipient_emails,
            fail_silently=False,
        )
    return f"Email sent to {len(recipient_emails)} users"

@shared_task
def generate_user_task_report(user_id):
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return f"User {user_id} does not exist"

    total_tasks = user.user_tasks.count()
    completed_tasks = user.user_tasks.filter(completed=True).count()
    incomplete_tasks = total_tasks - completed_tasks
    result = f"User {user_id} Task Report: Total: {total_tasks}, Completed: {completed_tasks}, Incomplete: {incomplete_tasks}"

    channel_layer = get_channel_layer()
    print("Sending WebSocket message...")
    async_to_sync(channel_layer.group_send)(
        "admin_notifications",
        {
            "type": "task_update",
            "operation": "Generate Report",
            "data": {"user_id": user_id},
            "result": result,
            "timestamp": timezone.now().isoformat()
        }
    )
    return result