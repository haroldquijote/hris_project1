from django.db import models
from django.conf import settings
from employees.models import Employee


class OvertimeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='overtime_requests'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_overtime'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.employee} – {self.date} ({self.status})"


class OvertimeConfiguration(models.Model):
    """Singleton to store overtime multipliers (editable by HR)."""
    ordinary_day_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.25)
    rest_day_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.69)
    special_non_working_holiday_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.69)
    special_day_on_rest_day_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.95)
    regular_holiday_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=2.60)
    regular_holiday_on_rest_day_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=3.38)
    rest_day_first8_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.30)
    special_non_working_first8_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.30)
    special_on_rest_day_first8_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.50)
    regular_holiday_first8_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    regular_on_rest_day_first8_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=2.60)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj