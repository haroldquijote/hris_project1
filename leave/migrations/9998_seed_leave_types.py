from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0001_initial'),
    ]

    operations = [
    ]
from django.db import migrations

def create_leave_types(apps, schema_editor):
    LeaveType = apps.get_model('leave', 'LeaveType')
    LeaveConfiguration = apps.get_model('leave', 'LeaveConfiguration')

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
        LeaveType.objects.get_or_create(name=name, defaults={'counts_towards_balance': counts})

    LeaveConfiguration.objects.get_or_create(pk=1, defaults={'annual_leave_days': 10})

class Migration(migrations.Migration):
    dependencies = [
        ('leave', '0001_initial'),   # Make sure this matches your actual previous migration file
    ]
    operations = [
        migrations.RunPython(create_leave_types),
    ]