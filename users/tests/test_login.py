import uuid
from datetime import timedelta

import jwt as pyjwt
from django.conf import settings
from django.test import override_settings
from django.urls import resolve, reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from access_control.models import Role
from services.jwt import issue_access_token
from users.models import AuthSession, User
from users.serializers import LoginSerializer, ProfilePatchSerializer
from users.views import LoginView, LogoutView, MeView, ProfileView


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


    def test_me_url_resolves_to_me_view(self):
        match = resolve("/api/auth/me/")

        self.assertIs(match.func.view_class, MeView)

    def test_me_returns_authenticated_user_profile(self):
        token = issue_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": self.user.id,
                "email": self.user.email,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "middle_name": self.user.middle_name,
                "role": {"code": "user", "name": "Пользователь"},
            },
        )

    def test_me_rejects_request_without_access_token(self):
        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")


    def test_me_rejects_invalid_bearer_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")

    def test_me_rejects_revoked_session(self):
        token = issue_access_token(self.user)
        session = AuthSession.objects.get(user=self.user)
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_rejects_expired_session(self):
        token = issue_access_token(self.user)
        session = AuthSession.objects.get(user=self.user)
        session.expires_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=["expires_at"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_logout_url_resolves_to_logout_view(self):
        match = resolve("/api/auth/logout/")

        self.assertIs(match.func.view_class, LogoutView)

    def test_logout_revokes_current_session_and_invalidates_token(self):
        token = issue_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        logout_response = self.client.post(reverse("logout"))
        session = AuthSession.objects.get(user=self.user)
        me_response = self.client.get(reverse("me"))

        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNotNone(session.revoked_at)
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_rejects_request_without_access_token(self):
        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")


    def test_profile_url_resolves_to_profile_view(self):
        match = resolve("/api/profile")

        self.assertIs(match.func.view_class, ProfileView)
        self.assertEqual(reverse("profile"), "/api/profile")

    def test_profile_returns_authenticated_user_data(self):
        token = issue_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "email": self.user.email,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "middle_name": self.user.middle_name,
            },
        )

    def test_profile_rejects_request_without_access_token(self):
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")


    def test_profile_patch_serializer_accepts_single_field(self):
        serializer = ProfilePatchSerializer(data={"first_name": " New name "})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, {"first_name": "New name"})

    def test_profile_patch_updates_only_submitted_fields(self):
        token = issue_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(
            reverse("profile"),
            {"first_name": "New name"},
            format="json",
        )
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.first_name, "New name")
        self.assertEqual(self.user.last_name, "Novikov")
        self.assertEqual(response.data["first_name"], "New name")

    def test_profile_patch_allows_current_email(self):
        token = issue_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(
            reverse("profile"),
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)

    def test_profile_patch_rejects_empty_payload(self):
        token = issue_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.patch(reverse("profile"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_patch_rejects_request_without_access_token(self):
        response = self.client.patch(
            reverse("profile"),
            {"first_name": "New name"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
