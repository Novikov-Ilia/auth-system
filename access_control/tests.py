from django.db import IntegrityError, transaction
from django.test import TestCase

from access_control.models import Role


class RoleModelTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(code='user', name='Пользователь')

    def test_string_representation_returns_name(self):
        self.assertEqual(str(self.role), 'Пользователь')

    def test_code_is_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Role.objects.create(code='user', name='Другой пользователь')

    def test_created_at_is_set_automatically(self):
        self.assertIsNotNone(self.role.created_at)

    def test_model_uses_roles_table(self):
        self.assertEqual(Role._meta.db_table, 'roles')
