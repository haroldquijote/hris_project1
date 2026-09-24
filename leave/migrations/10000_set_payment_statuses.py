from django.db import migrations


def set_payment_statuses(apps, schema_editor):
    LeaveType = apps.get_model('leave', 'LeaveType')

    unpaid = ['Vacation Leave', 'Sick Leave', 'Emergency Leave', 'Other']
    government = ['Maternity Leave', 'Paternity Leave', 'Solo Parent Leave']

    LeaveType.objects.filter(name__in=unpaid).update(payment_status='UNPAID')
    LeaveType.objects.filter(name__in=government).update(payment_status='GOVERNMENT')


def reverse_payment_statuses(apps, schema_editor):
    LeaveType = apps.get_model('leave', 'LeaveType')
    LeaveType.objects.all().update(payment_status='UNPAID')


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '9999_leavetype_payment_status'),   # ← change to your actual schema migration name
    ]

    operations = [
        migrations.RunPython(set_payment_statuses, reverse_payment_statuses),
    ]