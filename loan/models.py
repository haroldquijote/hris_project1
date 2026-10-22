from decimal import Decimal
from django.db import models
from django.conf import settings
from employees.models import Employee


class EmployeeLoan(models.Model):
    class LoanType(models.TextChoices):
        PAGIBIG = 'PAGIBIG', 'Pag-IBIG'
        SSS = 'SSS', 'SSS'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='loans',
    )
    loan_type = models.CharField(max_length=10, choices=LoanType.choices)
    custom_name = models.CharField(max_length=100, blank=True, null=True)
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    months_to_pay = models.PositiveIntegerField()
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    periods_paid = models.PositiveIntegerField(default=0)
    start_date = models.DateField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_loans',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.company_id} — {self.display_name} — ₱{self.balance}"

    def save(self, *args, **kwargs):
        # Initialize balance = principal on first save
        if not self.pk:
            self.balance = self.principal_amount
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        if self.loan_type == self.LoanType.OTHER and self.custom_name:
            return self.custom_name
        return self.get_loan_type_display()

    @property
    def total_periods(self):
        """Number of semi-monthly pay periods to fully pay off."""
        return self.months_to_pay * 2

    @property
    def monthly_amortization(self):
        """Full-month amortization."""
        return (self.principal_amount / Decimal(self.months_to_pay)).quantize(Decimal('0.01'))

    @property
    def per_period_amount(self):
        """Amount deducted each semi-monthly period (split in halves)."""
        return (self.principal_amount / Decimal(self.total_periods)).quantize(Decimal('0.01'))

    @property
    def months_paid(self):
        return self.periods_paid // 2

    @property
    def months_remaining(self):
        return self.months_to_pay - self.months_paid

    @property
    def progress_percent(self):
        if self.principal_amount <= 0:
            return 0
        paid = self.principal_amount - self.balance
        return float(round((paid / self.principal_amount) * 100, 2))

    def calculate_next_payment(self):
        """
        Amount to deduct this period.
        - Normal period: per_period_amount
        - Final period (balance < per_period_amount): deduct remaining balance exactly
        - Already paid off: 0
        """
        if self.balance <= Decimal('0.01'):
            return Decimal('0.00')
        if self.balance < self.per_period_amount:
            return self.balance
        return self.per_period_amount


class LoanPayment(models.Model):
    loan = models.ForeignKey(
        EmployeeLoan, on_delete=models.CASCADE, related_name='payments',
    )
    pay_period = models.ForeignKey(
        'payroll.PayPeriod', on_delete=models.PROTECT, related_name='loan_payments',
    )
    payslip = models.ForeignKey(
        'payroll.Payslip', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='loan_payments',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reversed_loan_payments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['loan', 'pay_period']
        ordering = ['-pay_period__start_date']

    def __str__(self):
        return f"{self.loan} — {self.pay_period} — ₱{self.amount}"