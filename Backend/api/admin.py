from django.contrib import admin
from .models import CustomUser, Task


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'gender', 'birth_date', 'avatar')
    search_fields = ('email', 'username')
    list_filter = ('gender',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'completed', 'created_at')
    search_fields = ('title',)
    list_filter = ('completed', 'user')