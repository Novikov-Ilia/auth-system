import uuid

import jwt as pyjwt
from django.conf import settings
from django.test import override_settings
from django.urls import resolve, reverse
from rest_framework import status
from rest_framework.test import APITestCase

from access_control.models import Role
from services.jwt import issue_access_token
from users.models import AuthSession, User
from users.serializers import LoginSerializer
from users.views import LoginView


@override_settings(
    JWT_SECRET_KEY="test-jwt-secret-at-least-32-bytes-long",
    JWT_ALGORITHM="HS256",
    JWT_ACCESS_TTL_MINUTES=60,
)
class LoginTests(APITestCase):
    password = "StrongPassword123!"

    def setUp(self):
        self.role, _ = Role.objects.get_or_create(
            code="user",
            defaults={"name": "Пользователь"},
        )
        self.user = User.objects.create_user(
            email="user@example.com",
            password=self.password,
            first_name="Ilya",
            last_name="Novikov",
            role=self.role,
        )
        self.payload = {
            "email": "USER@EXAMPLE.COM",
            "password": self.password,
        }

    def test_login_serializer_authenticates_user(self):
        serializer = LoginSerializer(data=self.payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["user"], self.user)
        self.assertTrue(serializer.fields["password"].write_only)

    def test_login_serializer_rejects_unknown_email_and_wrong_password(self):
        for payload in (
            {"email": "unknown@example.com", "password": self.password},
            {"email": self.user.email, "password": "WrongPassword123!"},
        ):
            with self.subTest(payload=payload):
                serializer = LoginSerializer(data=payload)

                self.assertFalse(serializer.is_valid())
                self.assertIn("non_field_errors", serializer.errors)

    def test_login_serializer_rejects_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        serializer = LoginSerializer(data=self.payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_issue_access_token_creates_session_with_matching_jti(self):
        token = issue_access_token(self.user)

        payload = pyjwt.decode(
            token,
            key=settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        session = AuthSession.objects.get(jti=uuid.UUID(payload["jti"]))

        self.assertEqual(payload["sub"], str(self.user.pk))
        self.assertEqual(payload["type"], "access")
        self.assertEqual(session.user, self.user)
        self.assertTrue(session.is_active)

    def test_login_url_resolves_to_login_view(self):
        match = resolve("/api/auth/login/")

        self.assertIs(match.func.view_class, LoginView)

    def test_login_returns_access_token_and_creates_session(self):
        response = self.client.post(reverse("login"), self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data),
            {"access_token", "token_type", "expires_in"},
        )
        self.assertEqual(response.data["token_type"], "Bearer")
        self.assertEqual(
            response.data["expires_in"],
            settings.JWT_ACCESS_TTL_MINUTES * 60,
        )
        self.assertEqual(AuthSession.objects.filter(user=self.user).count(), 1)

    def test_login_rejects_invalid_credentials_without_creating_session(self):
        self.payload["password"] = "WrongPassword123!"

        response = self.client.post(reverse("login"), self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertEqual(AuthSession.objects.count(), 0)
