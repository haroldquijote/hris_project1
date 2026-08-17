from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile

class Command(BaseCommand):
    help = 'Create an HR Admin user'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--company_id', required=True)   # optional, link to employee

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        company_id = options.get('company_id')

        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True
        user.save()

        profile, created = Profile.objects.get_or_create(user=user)
        profile.role = "HRADMIN"
        profile.must_change_password = False

        if company_id:
            from employees.models import Employee
            try:
                employee = Employee.objects.get(company_id=company_id)
                profile.employee = employee
            except Employee.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Employee with company_id {company_id} not found; profile created without employee link."))

        profile.save()

        self.stdout.write(self.style.SUCCESS(f'HR Admin "{username}" created successfully.'))