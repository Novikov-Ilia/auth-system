from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import exceptions

from access_control.models import AccessRoleRule, BusinessElement, Role
from access_control.services.permissions import Permissions
from users.models import User


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



class PermissionsTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(code="manager", name="Менеджер")
        self.user = User.objects.create_user(
            email="manager@example.com",
            password="StrongPassword123!",
            first_name="Ilya",
            last_name="Novikov",
            role=self.role,
        )
        self.element = BusinessElement.objects.create(
            code="products",
            name="Products",
            description="Demo products",
        )
        self.rule = AccessRoleRule.objects.create(
            role=self.role,
            element=self.element,
        )
        self.permissions = Permissions()

    def test_rule_without_permissions_denies_access(self):
        with self.assertRaises(exceptions.PermissionDenied):
            self.permissions.check_permission(
                self.user,
                element_code="products",
                action="read",
                owner_id=self.user.pk,
            )

    def test_own_object_permissions_allow_matching_actions(self):
        for action, field_name in (
            ("read", "read_permission"),
            ("update", "update_permission"),
            ("delete", "delete_permission"),
        ):
            with self.subTest(action=action):
                setattr(self.rule, field_name, True)
                self.rule.save(update_fields=[field_name])

                self.permissions.check_permission(
                    self.user,
                    element_code="products",
                    action=action,
                    owner_id=self.user.pk,
                )

    def test_all_permissions_allow_access_to_other_users_object(self):
        for action, field_name in (
            ("read", "read_all_permission"),
            ("update", "update_all_permission"),
            ("delete", "delete_all_permission"),
        ):
            with self.subTest(action=action):
                setattr(self.rule, field_name, True)
                self.rule.save(update_fields=[field_name])

                self.permissions.check_permission(
                    self.user,
                    element_code="products",
                    action=action,
                    owner_id=self.user.pk + 1,
                )

    def test_own_object_permission_does_not_allow_other_users_object(self):
        self.rule.read_permission = True
        self.rule.save(update_fields=["read_permission"])

        with self.assertRaises(exceptions.PermissionDenied):
            self.permissions.check_permission(
                self.user,
                element_code="products",
                action="read",
                owner_id=self.user.pk + 1,
            )

    def test_is_staff_does_not_bypass_access_rule(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        with self.assertRaises(exceptions.PermissionDenied):
            self.permissions.check_permission(
                self.user,
                element_code="products",
                action="read",
                owner_id=self.user.pk,
            )

    def test_create_requires_create_permission(self):
        with self.assertRaises(exceptions.PermissionDenied):
            self.permissions.check_permission(
                self.user,
                element_code="products",
                action="create",
            )

        self.rule.create_permission = True
        self.rule.save(update_fields=["create_permission"])

        self.permissions.check_permission(
            self.user,
            element_code="products",
            action="create",
        )

    def test_missing_rule_denies_access(self):
        BusinessElement.objects.create(
            code="orders",
            name="Orders",
            description="Demo orders",
        )

        with self.assertRaises(exceptions.PermissionDenied):
            self.permissions.check_permission(
                self.user,
                element_code="orders",
                action="read",
                owner_id=self.user.pk,
            )

    def test_anonymous_user_is_not_authenticated(self):
        with self.assertRaises(exceptions.NotAuthenticated):
            self.permissions.check_permission(
                AnonymousUser(),
                element_code="products",
                action="read",
                owner_id=self.user.pk,
            )

    def test_unknown_action_is_denied(self):
        with self.assertRaises(exceptions.PermissionDenied):
            self.permissions.check_permission(
                self.user,
                element_code="products",
                action="publish",
            )
