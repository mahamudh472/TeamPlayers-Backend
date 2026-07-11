import json
import tempfile
import os
from django.test import TestCase
from django.core.management import call_command
from apps.finance.models import Plan
from apps.finance.services import seed_subscription_plans

class SubscriptionPlanSeedingTests(TestCase):
    def setUp(self):
        # Setup temporary directories and JSON files for isolated testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file_path = os.path.join(self.temp_dir.name, 'test_plans.json')
        
        self.test_data = [
            {
                "plan_name": "Test Starter",
                "description": "Perfect for testing",
                "price": 49.99,
                "currency": "USD",
                "interval": "month",
                "feature_list": ["Feature A", "Feature B"]
            },
            {
                "plan_name": "Test Enterprise",
                "description": "Enterprise test",
                "price": 499.99,
                "currency": "USD",
                "interval": "year",
                "feature_list": ["All features"]
            }
        ]
        with open(self.temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seed_subscription_plans_creates_records(self):
        # Verify database is empty initially
        self.assertEqual(Plan.objects.count(), 0)

        # Run the seed function with temp file
        results = seed_subscription_plans(file_path=self.temp_file_path)

        # Check results
        self.assertEqual(results['created'], 2)
        self.assertEqual(results['updated'], 0)
        self.assertEqual(Plan.objects.count(), 2)

        # Retrieve and verify plan attributes
        starter = Plan.objects.get(name="Test Starter")
        self.assertEqual(starter.description, "Perfect for testing")
        self.assertEqual(float(starter.price), 49.99)
        self.assertEqual(starter.currency, "USD")
        self.assertEqual(starter.interval, "month")
        
        # Verify feature list JSON string format
        features = json.loads(starter.feature_list)
        self.assertEqual(features, ["Feature A", "Feature B"])

    def test_seed_subscription_plans_no_duplicates(self):
        # Run seed first time
        seed_subscription_plans(file_path=self.temp_file_path)
        self.assertEqual(Plan.objects.count(), 2)

        # Modify one plan's price in the JSON data
        self.test_data[0]['price'] = 59.99
        self.test_data[0]['description'] = "Updated description"
        with open(self.temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_data, f)

        # Run seed second time
        results = seed_subscription_plans(file_path=self.temp_file_path)

        # Verify no duplicates were created
        self.assertEqual(results['created'], 0)
        self.assertEqual(results['updated'], 2)
        self.assertEqual(Plan.objects.count(), 2)

        # Verify updating works
        starter = Plan.objects.get(name="Test Starter")
        self.assertEqual(float(starter.price), 59.99)
        self.assertEqual(starter.description, "Updated description")

    def test_management_command_execution(self):
        # Test executing the management command via call_command
        self.assertEqual(Plan.objects.count(), 0)
        
        # Executing the command seeds the default assets file
        call_command('add_subscription_plans')
        
        # Verify actual plans from settings.BASE_DIR/assets/subscription_plans.json are created
        self.assertTrue(Plan.objects.filter(name="Starter").exists())
        self.assertTrue(Plan.objects.filter(name="Growth").exists())
        self.assertTrue(Plan.objects.filter(name="Scale").exists())
        self.assertTrue(Plan.objects.filter(name="Enterprise").exists())
