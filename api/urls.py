from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    RegisterView, LoginView, ProfileView, AboutView, TaskListView, TaskDetailView, admin_online_users_view, test_ws_view, SharedTasksView, send_notification, generate_task_report
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('about/', AboutView.as_view(), name='about'),
    path('tasks/', TaskListView.as_view(), name='task-list'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('shared-tasks/', SharedTasksView.as_view(), name='shared-tasks'),
    path('admin/online-users/', admin_online_users_view, name='admin_online_users'),
    path('test-ws/', test_ws_view, name='test_ws'),
    path('send-notification/', send_notification, name='send_notification'),
    path('generate-task-report/', generate_task_report, name='generate_task_report'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)