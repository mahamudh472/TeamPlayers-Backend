from django.core.management.base import BaseCommand
from apps.finance.services import seed_subscription_plans

class Command(BaseCommand):
    help = 'Seeds or updates subscription plans from the subscription_plans.json asset file'

    def handle(self, *args, **options):
        self.stdout.write("Starting to seed subscription plans...")
        try:
            results = seed_subscription_plans()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully processed subscription plans.\n"
                    f"Created: {results['created']}\n"
                    f"Updated/Skipped duplicates: {results['updated']}"
                )
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Error seeding subscription plans: {str(e)}")
            )
