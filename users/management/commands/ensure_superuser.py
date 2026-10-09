import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a superuser if one does not already exist'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('SUPERUSER_USERNAME')
        password = os.environ.get('SUPERUSER_PASSWORD')
        email = os.environ.get('SUPERUSER_EMAIL', '')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                'SUPERUSER_USERNAME or SUPERUSER_PASSWORD not set — skipping.'
            ))
            return

        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        # Ensure Profile exists and has HRADMIN role
        from users.models import Profile
        profile, profile_created = Profile.objects.get_or_create(user=user)
        profile.role = 'HRADMIN'                
        profile.must_change_password = False        
        profile.save()                              

        if profile_created:
            self.stdout.write(self.style.SUCCESS(
                f'Profile created for superuser "{username}".'
            ))

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" {action} with HRADMIN role.'))