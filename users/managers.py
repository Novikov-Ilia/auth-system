from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    @staticmethod
    def normalize_email(email: str) -> str:
        email = email.strip()

        if not email:
            raise ValueError('Введена пустая почта')
        
        return email.lower()

    def create_user(self, /, email: str, passwd: str, **extra_fields: dict):
        if not email:
            raise ValueError("Email обязателен")

        if not passwd:
            raise ValueError("Пароль обязателен")

        norm_email = UserManager.normalize_email(email)
        
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)

        user = self.model(
            email=norm_email,
            **extra_fields,
        )
        user.set_password(passwd)
        user.save()

        return user

    def create_superuser(self, /, email: str, passwd: str, **extra_fields: dict):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "У суперпользователя is_staff должен быть True"
            )

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "У суперпользователя is_superuser должен быть True"
            )

        return self.create_user(email=email, passwd=passwd, **extra_fields)