from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.validators import UniqueValidator
from rest_framework import serializers
from .models import User
from access_control.models import Role
from .managers import UserManager


class RegistrationSerializer(serializers.ModelSerializer):
    repeat_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                lookup='iexact',
                message='Пользователь с таким email уже существует.',
            ),
        ],
    )
    class Meta:
        model = User
        fields = [
            'repeat_password',
            'password',
            'email',
            'first_name',
            'last_name', 
            'middle_name',
        ]
        extra_kwargs = {
            "password": {
                "write_only": True,
            },
        }


    def validate_password(self, password: str, user=None) -> str:
        try:
            django_validate_password(password, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error

        return password

    def validate(self, attrs: dict) -> dict:
        password = attrs.get('password')
        repeat_password = attrs.get('repeat_password')

        if not password == repeat_password:
            raise DjangoValidationError('Пароли должны совпадать')
        
        return attrs
    
    def create(self, validated_data: dict)  -> User:
        validated_data.pop('repeat_password')
        password = validated_data.pop("password")
        email = validated_data.pop("email")
        role = Role.objects.get(code="user")

        return User.objects.create_user(
            email=email,
            password=password,
            role=role,
            **validated_data,
        )
    

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs) -> dict:
        email = UserManager.normalize_email(attrs.get('email'))
        password = attrs.get('password')

        user = User.objects.filter(email=email).first()

        if not user or not user.is_active or not user.check_password(password):
            raise serializers.ValidationError('Неверный email или пароль')
        
        return {
            'user': user,
        }
