from django.db import models
from django.conf import settings
from employees.models import Employee


class LeaveConfiguration(models.Model):
    """Singleton to hold global leave settings (annual leave days)."""
    annual_leave_days = models.PositiveSmallIntegerField(default=10)

    def save(self, *args, **kwargs):
        # Ensure only one configuration row exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    counts_towards_balance = models.BooleanField(
        default=True,
        help_text="If True, approved leaves of this type deduct from the annual pool."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class LeaveGrant(models.Model):
    """
    A one‑off grant of annual leave days, credited on Jan 1 of the year
    following the year worked. Expires on April 30 of the second year after credit.
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='leave_grants'
    )
    granted_days = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField(help_text="Year the work was performed (e.g., 2025)")
    credited_on = models.DateField(help_text="Date the leave becomes available")
    expires_on = models.DateField(help_text="Date after which leave is forfeited")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} – {self.granted_days} days ({self.year})"

    class Meta:
        ordering = ['-year', '-credited_on']


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='requests'
    )
    custom_leave_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Only used when leave type is 'Other'"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leaves'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_days(self):
        """Return inclusive day count."""
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"{self.employee} – {self.leave_type} ({self.start_date} to {self.end_date})"

    class Meta:
        ordering = ['-created_at']


class LeaveAdjustment(models.Model):
    """Manual addition or deduction of days, with a reason."""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='leave_adjustments'
    )
    amount = models.IntegerField(help_text="Positive = add days, negative = deduct days")
    reason = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='leave_adjustments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} – {self.amount} day(s) ({self.reason[:30]})"

    class Meta:
        ordering = ['-created_at']
