from django.test import TestCase, Client
from apps.accounts.models import User

class LoginAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="[EMAIL_ADDRESS]", password="[PASSWORD]")

    def test_login(self):
        response = self.client.post('/api/accounts/login/', {
            "email": "[EMAIL_ADDRESS]",
            "password": "[PASSWORD]",
        })
        self.assertEqual(response.status_code, 200)

        
    def test_register(self):
        response = self.client.post('/api/accounts/register/', {
            "email": "[EMAIL_ADDRESS]",
            "password": "[PASSWORD]",
        })
        self.assertEqual(response.status_code, 201)

    def test_logout(self):
        response = self.client.post('/api/accounts/logout/', {
            "refresh": "token",
        })
        self.assertEqual(response.status_code, 200)
