from rest_framework import serializers
from .models import CustomUser, Task


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'gender', 'birth_date', 'avatar']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            gender=validated_data['gender'],
            birth_date=validated_data['birth_date'],
            avatar=validated_data.get('avatar', None)
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'gender', 'birth_date', 'avatar']


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'completed', 'created_at']