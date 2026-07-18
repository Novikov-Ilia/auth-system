import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from access_control.models import Role
from users.models import AuthSession, User


class AuthSessionModelTests(TestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(
            code='user',
            defaults={'name': 'Пользователь'},
        )
        self.user = User.objects.create_user(
            email='user@example.com',
            password='StrongPassword123!',
            first_name='Ilya',
            last_name='Novikov',
            role=self.role,
        )

    def create_session(self, **overrides):
        data = {
            'user': self.user,
            'expires_at': timezone.now() + timedelta(hours=1),
        }
        data.update(overrides)
        return AuthSession.objects.create(**data)

    def test_session_uses_uuid_identifiers_and_is_linked_to_user(self):
        session = self.create_session()

        self.assertIsInstance(session.pk, uuid.UUID)
        self.assertIsInstance(session.jti, uuid.UUID)
        self.assertIsNotNone(session.created_at)
        self.assertEqual(list(self.user.auth_sessions.all()), [session])

    def test_jti_is_unique(self):
        jti = uuid.uuid4()
        self.create_session(jti=jti)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_session(jti=jti)

    def test_string_representation_contains_user_email_and_jti(self):
        session = self.create_session()

        self.assertEqual(str(session), f'{self.user.email}: {session.jti}')

    def test_active_session_is_active(self):
        self.assertTrue(self.create_session().is_active)

    def test_revoked_session_is_not_active(self):
        session = self.create_session(revoked_at=timezone.now())

        self.assertFalse(session.is_active)

    def test_expired_session_is_not_active(self):
        session = self.create_session(
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.assertFalse(session.is_active)
