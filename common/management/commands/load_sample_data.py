from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Load sample data for call center use case'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading sample data...'))

        # Create superuser if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Created admin user (username: admin, password: admin123)'))

        # Load fixtures
        call_command('loaddata', 'fixtures/sample_data.json')

        self.stdout.write(self.style.SUCCESS('Sample data loaded successfully!'))
        self.stdout.write(self.style.WARNING('Sample data includes:'))
        self.stdout.write('- Call Center Analytics Project')
        self.stdout.write('- Intent Classifier Agent with system/user prompts')
        self.stdout.write('- OpenAI GPT-4 tool configuration')
        self.stdout.write('- Daily Intent Analysis Workflow')
        self.stdout.write('- Complete placeholder mappings for call transcript data')