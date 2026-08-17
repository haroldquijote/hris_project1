from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    employee = models.OneToOneField(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="profile",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---------- RBAC ----------
    class Role(models.TextChoices):
        HRADMIN = 'HRADMIN', 'HR Admin'
        HRASSISTANT = 'HRASSISTANT', 'HR Assistant'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.HRASSISTANT,
    )
    must_change_password = models.BooleanField(default=False)

    # Temporary privilege grants (admin toggles these per assistant)
    can_manage_leave = models.BooleanField(default=False)
    can_manage_overtime = models.BooleanField(default=False)
    can_manage_employees = models.BooleanField(default=False)
    can_delete_records = models.BooleanField(default=False)
    can_lock_payroll = models.BooleanField(default=False)
    can_manage_leave_adjustments = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.employee}"