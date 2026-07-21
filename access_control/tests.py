from django.db import IntegrityError, transaction
from django.test import TestCase

from access_control.models import AccessRoleRule, BusinessElement, Role


class RoleModelTests(TestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(
            code='user',
            defaults={'name': 'Пользователь'},
        )

    def test_initial_roles_are_available(self):
        roles = dict(
            Role.objects.filter(code__in=['user', 'admin']).values_list('code', 'name')
        )

        self.assertEqual(
            roles,
            {
                'user': 'Пользователь',
                'admin': 'Администратор',
            },
        )

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



class AccessRoleRuleModelTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(code="manager", name="Менеджер")
        self.element = BusinessElement.objects.create(
            code="products",
            name="Products",
            description="Demo products",
        )

    def test_rule_defaults_to_no_permissions(self):
        rule = AccessRoleRule.objects.create(
            role=self.role,
            element=self.element,
        )

        self.assertFalse(rule.read_permission)
        self.assertFalse(rule.read_all_permission)
        self.assertFalse(rule.create_permission)
        self.assertFalse(rule.update_permission)
        self.assertFalse(rule.update_all_permission)
        self.assertFalse(rule.delete_permission)
        self.assertFalse(rule.delete_all_permission)
        self.assertEqual(str(rule), "manager: products")

    def test_rule_is_unique_for_role_and_element(self):
        AccessRoleRule.objects.create(role=self.role, element=self.element)

        with self.assertRaises(IntegrityError), transaction.atomic():
            AccessRoleRule.objects.create(role=self.role, element=self.element)
