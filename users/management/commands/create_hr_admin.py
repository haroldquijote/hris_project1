import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile
from employees.models import Employee


class Command(BaseCommand):
    help = 'Create an HR Admin user linked to an employee'

    def add_arguments(self, parser):
        parser.add_argument('--company_id', required=False)
        parser.add_argument('--password', required=False)

    def handle(self, *args, **options):
        company_id = options.get('company_id') or os.environ.get('HRADMIN_COMPANY_ID')
        password = options.get('password') or os.environ.get('HRADMIN_PASSWORD')

        if not company_id or not password:
            self.stdout.write(self.style.WARNING(
                'company_id or password not set — skipping.'
            ))
            return

        # Look up the employee
        try:
            employee = Employee.objects.get(company_id=company_id)
        except Employee.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'Employee with company_id "{company_id}" does not exist. Aborting.'
            ))
            return

        # Derive username from employee (use company_id as username)
        username = company_id.lower()

        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = "HRADMIN"
        profile.must_change_password = False
        profile.employee = employee
        profile.save()

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(
            f'HR Admin "{username}" {action} and linked to Employee {company_id}.'
        ))