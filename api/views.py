from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import Task
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer, TaskSerializer
)


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        """Реєстрація нового користувача. Приймає дані користувача (username, email, password, gender, birth_date, avatar) і створює нового користувача в системі."""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        """Аутентифікація користувача та видача JWT-токенів. Приймає email і пароль, повертає access та refresh токени для авторизованого користувача."""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            )
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Отримання профілю авторизованого користувача.Повертає дані профілю (username, email, gender, birth_date, avatar)."""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """Оновлення профілю авторизованого користувача.Дозволяє частково оновити дані профілю, включаючи аватар."""
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AboutView(APIView):
    def get(self, request):
        """Інформація про додаток. Повертає логотип і короткий опис додатку To-Do List."""
        return Response({
            'logo': request.build_absolute_uri('/static/img/logo.png'),
            'description': 'A simple To-Do List application'
        })


class TaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Отримання списку задач авторизованого користувача.Повертає всі задачі користувача з опціональним фільтром за параметром `completed` (true/false)."""
        completed_param = request.query_params.get('completed', None)
        tasks = Task.objects.filter(user=request.user)
        if completed_param is not None:
            completed = completed_param.lower() == 'true'
            tasks = tasks.filter(completed=completed)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Створення нової задачі для авторизованого користувача. Приймає дані задачі (title, description, completed) і пов’язує її з поточним користувачем."""
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Task.objects.get(pk=pk, user=user)
        except Task.DoesNotExist:
            return None

    def get(self, request, pk):
        """Отримання деталей конкретної задачі. Повертає дані задачі за її ID, якщо вона належить авторизованому користувачу."""
        task = self.get_object(pk, request.user)
        if task is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    def put(self, request, pk):
        """Оновлення конкретної задачі. Дозволяє частково оновити задачу за її ID, якщо вона належить авторизованому користувачу."""
        task = self.get_object(pk, request.user)
        if task is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Видалення конкретної задачі.Видаляє задачу за її ID, якщо вона належить авторизованому користувачу."""
        task = self.get_object(pk, request.user)
        if task is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)