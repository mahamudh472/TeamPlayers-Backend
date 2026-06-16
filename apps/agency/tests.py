from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.agency.models import Agency, AgencyMember

class AgencyRegistrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registration_with_agency_name(self):
        email = "test@example.com"
        password = "password123"
        agency_name = "My Custom Agency"
        
        response = self.client.post('/api/v1/accounts/register/', {
            "email": email,
            "password": password,
            "agency_name": agency_name,
            "full_name": "Test User"
        })
        
        self.assertEqual(response.status_code, 201)
        
        # Check if user was created
        user = User.objects.get(email=email)
        self.assertIsNotNone(user)
        
        # Check if agency was created with the custom name
        agency = Agency.objects.filter(name=agency_name).first()
        self.assertIsNotNone(agency)
        self.assertEqual(agency.name, agency_name)
        
        # Check if user is owner of the agency
        member = AgencyMember.objects.get(agency=agency, user=user)
        self.assertEqual(member.role, 'owner')

    def test_registration_without_agency_name(self):
        email = "test2@example.com"
        password = "password123"
        full_name = "Test User 2"
        
        response = self.client.post('/api/v1/accounts/register/', {
            "email": email,
            "password": password,
            "full_name": full_name
        })
        
        self.assertEqual(response.status_code, 201)
        
        # Check if agency was created with default name
        expected_name = f"{full_name}'s Agency"
        agency = Agency.objects.filter(name=expected_name).first()
        self.assertIsNotNone(agency)
