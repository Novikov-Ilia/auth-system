from django.test import TestCase

from access_control.models import Role
from users.models import User
from users.serializers import RegistrationSerializer


class RegistrationSerializerTests(TestCase):
    password = 'StrongPassword123!'

    def setUp(self):
        self.role, _ = Role.objects.get_or_create(
            code='user',
            defaults={'name': 'Пользователь'},
        )
        self.payload = {
            'first_name': 'Илья',
            'last_name': 'Новиков',
            'middle_name': 'Дмитриевич',
            'email': 'User@EXAMPLE.COM',
            'password': self.password,
            'repeat_password': self.password,
        }

    def test_exposes_expected_registration_fields(self):
        serializer = RegistrationSerializer()

        self.assertEqual(
            set(serializer.fields),
            {
                'first_name',
                'last_name',
                'middle_name',
                'email',
                'password',
                'repeat_password',
            },
        )
        self.assertTrue(serializer.fields['password'].write_only)
        self.assertTrue(serializer.fields['repeat_password'].write_only)

    def test_valid_payload_passes_validation(self):
        serializer = RegistrationSerializer(data=self.payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_middle_name_is_optional(self):
        self.payload.pop('middle_name')
        serializer = RegistrationSerializer(data=self.payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_required_fields_are_validated(self):
        required_fields = {
            'first_name',
            'last_name',
            'email',
            'password',
            'repeat_password',
        }

        for field in required_fields:
            with self.subTest(field=field):
                payload = self.payload.copy()
                payload.pop(field)
                serializer = RegistrationSerializer(data=payload)

                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_invalid_email_is_rejected(self):
        self.payload['email'] = 'not-an-email'
        serializer = RegistrationSerializer(data=self.payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            email='user@example.com',
            passwd=self.password,
            first_name='Илья',
            last_name='Новиков',
            role=self.role,
        )
        self.payload['email'] = 'user@EXAMPLE.COM'
        serializer = RegistrationSerializer(data=self.payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_weak_password_is_rejected(self):
        self.payload['password'] = '123'
        self.payload['repeat_password'] = '123'
        serializer = RegistrationSerializer(data=self.payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_password_mismatch_is_rejected(self):
        self.payload['repeat_password'] = 'DifferentPassword123!'
        serializer = RegistrationSerializer(data=self.payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_save_creates_user_with_role_and_hashed_password(self):
        serializer = RegistrationSerializer(data=self.payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertEqual(user.role, self.role)
        self.assertEqual(user.email, 'user@example.com')
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(hasattr(user, 'repeat_password'))

    def test_serialized_response_does_not_expose_passwords(self):
        serializer = RegistrationSerializer(data=self.payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        response_data = RegistrationSerializer(user).data

        self.assertNotIn('password', response_data)
        self.assertNotIn('repeat_password', response_data)
