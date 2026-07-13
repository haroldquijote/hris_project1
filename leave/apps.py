from django.apps import AppConfig

class LeaveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leave'

    def ready(self):
        # Import models and run initial data setup after the app registry is fully loaded
        from .models import LeaveType, LeaveConfiguration

        # Create leave types if they don't already exist
        types = [
            ('Vacation Leave', True),
            ('Sick Leave', True),
            ('Emergency Leave', True),
            ('Maternity Leave', False),
            ('Paternity Leave', False),
            ('Solo Parent Leave', False),
            ('Other', False),
        ]
        for name, counts in types:
            LeaveType.objects.get_or_create(
                name=name,
                defaults={'counts_towards_balance': counts}
            )

        # Ensure the global configuration exists
        LeaveConfiguration.objects.get_or_create(pk=1, defaults={'annual_leave_days': 10})
