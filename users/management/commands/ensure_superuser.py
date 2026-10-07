import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a superuser if one does not already exist'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('SUPERUSER_USERNAME')
        email = os.environ.get('SUPERUSER_EMAIL', '')
        password = os.environ.get('SUPERUSER_PASSWORD')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                'SUPERUSER_USERNAME or SUPERUSER_PASSWORD not set — skipping.'
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(
                f'Superuser "{username}" already exists. Skipping.'
            ))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Superuser "{username}" created.'
        ))