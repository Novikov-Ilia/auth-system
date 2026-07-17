from django.urls import resolve, reverse
from rest_framework import status
from rest_framework.test import APITestCase

from access_control.models import Role
from users.models import User
from users.views import RegistrationView


class RegistrationViewTests(APITestCase):
    password = 'StrongPassword123!'

    def setUp(self):
        self.role = Role.objects.create(code='user', name='Пользователь')
        self.payload = {
            'first_name': 'Илья',
            'last_name': 'Новиков',
            'middle_name': 'Дмитриевич',
            'email': 'User@EXAMPLE.COM',
            'password': self.password,
            'repeat_password': self.password,
        }

    def register(self, payload=None):
        return self.client.post(
            reverse('register'),
            payload or self.payload,
            format='json',
        )

    def test_register_url_resolves_to_registration_view(self):
        match = resolve('/api/auth/register/')

        self.assertIs(match.func.view_class, RegistrationView)

    def test_register_creates_user_and_returns_201(self):
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(pk=response.data['id'])
        self.assertEqual(user.email, 'user@example.com')
        self.assertEqual(user.role, self.role)
        self.assertTrue(user.check_password(self.password))

    def test_register_response_does_not_expose_passwords(self):
        response = self.register()

        self.assertNotIn('password', response.data)
        self.assertNotIn('repeat_password', response.data)
        self.assertEqual(set(response.data), {'id', 'email'})

    def test_register_allows_omitted_middle_name(self):
        payload = self.payload.copy()
        payload.pop('middle_name')

        response = self.register(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get().middle_name, '')

    def test_register_rejects_duplicate_email_case_insensitively(self):
        User.objects.create_user(
            email='user@example.com',
            passwd=self.password,
            first_name='Илья',
            last_name='Новиков',
            role=self.role,
        )

        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_register_rejects_mismatched_passwords(self):
        payload = self.payload.copy()
        payload['repeat_password'] = 'DifferentPassword123!'

        response = self.register(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_register_rejects_weak_password(self):
        payload = self.payload.copy()
        payload['password'] = '123'
        payload['repeat_password'] = '123'

        response = self.register(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertEqual(User.objects.count(), 0)
