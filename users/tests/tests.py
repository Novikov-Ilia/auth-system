from django.contrib.auth.hashers import identify_hasher
from django.db import IntegrityError, transaction
from django.db.models.deletion import RestrictedError
from django.test import TestCase

from access_control.models import Role
from users.managers import UserManager
from users.models import User


class UserModelTests(TestCase):
    password = 'StrongPassword123!'

    def setUp(self):
        self.role, _ = Role.objects.get_or_create(
            code='user',
            defaults={'name': 'Пользователь'},
        )

    def create_user(self, **overrides):
        data = {
            'email': 'User@EXAMPLE.COM',
            'passwd': self.password,
            'first_name': 'Илья',
            'last_name': 'Новиков',
            'role': self.role,
        }
        data.update(overrides)
        return User.objects.create_user(**data)

    def test_field_configuration_matches_contract(self):
        self.assertFalse(User._meta.get_field('first_name').blank)
        self.assertFalse(User._meta.get_field('last_name').blank)
        self.assertTrue(User._meta.get_field('middle_name').blank)
        self.assertTrue(User._meta.get_field('email').unique)
        self.assertTrue(User._meta.get_field('is_active').default)
        self.assertFalse(User._meta.get_field('is_staff').default)
        self.assertTrue(User._meta.get_field('deleted_at').null)

    def test_create_user_returns_saved_user_with_defaults(self):
        user = self.create_user()

        self.assertIsInstance(user, User)
        self.assertIsNotNone(user.pk)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNone(user.deleted_at)
        self.assertEqual(user.role, self.role)

    def test_create_user_normalizes_email_and_hashes_password(self):
        user = self.create_user()

        self.assertEqual(user.email, 'user@example.com')
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))

    def test_create_user_stores_password_with_bcrypt(self):
        user = self.create_user()

        self.assertEqual(identify_hasher(user.password).algorithm, 'bcrypt_sha256')

    def test_created_and_updated_timestamps_are_set(self):
        user = self.create_user()

        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

    def test_email_is_unique(self):
        self.create_user()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_user()

    def test_role_reverse_relation_contains_user(self):
        user = self.create_user()

        self.assertEqual(list(self.role.users.all()), [user])

    def test_used_role_cannot_be_deleted(self):
        self.create_user()

        with self.assertRaises(RestrictedError):
            self.role.delete()

    def test_create_superuser_returns_user_with_required_flags(self):
        user = User.objects.create_superuser(
            email='Admin@EXAMPLE.COM',
            passwd=self.password,
            first_name='Илья',
            last_name='Новиков',
            role=self.role,
        )

        self.assertIsInstance(user, User)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.email, 'admin@example.com')

    def test_create_superuser_rejects_invalid_flags(self):
        with self.assertRaisesMessage(
            ValueError,
            'У суперпользователя is_staff должен быть True',
        ):
            User.objects.create_superuser(
                email='admin@example.com',
                passwd=self.password,
                first_name='Илья',
                last_name='Новиков',
                role=self.role,
                is_staff=False,
            )

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')


class UserManagerTests(TestCase):
    def test_normalize_email_strips_spaces_and_lowercases_email(self):
        normalized = UserManager.normalize_email('  Local.Part@EXAMPLE.COM  ')

        self.assertEqual(normalized, 'local.part@example.com')

    def test_normalize_email_rejects_empty_value(self):
        with self.assertRaises(ValueError):
            UserManager.normalize_email('   ')
