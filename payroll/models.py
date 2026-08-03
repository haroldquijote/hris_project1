from django.db import models
from employees.models import Employee
from django.conf import settings


class PayPeriod(models.Model):
    locked_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='locked_periods'
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    unlocked_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='unlocked_periods'
)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    class PeriodType(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular'
        THIRTEENTH_MONTH = 'THIRTEENTH_MONTH', '13th Month Pay'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        LOCKED = 'LOCKED', 'Locked'
        
    period_type = models.CharField(
        max_length=20,
        choices=PeriodType.choices,
        default=PeriodType.REGULAR,
    )
    
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"Pay Period: {self.start_date} – {self.end_date} ({self.status})"


class Payslip(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        FINAL = 'FINAL', 'Final'

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='payslips',
    )
    pay_period = models.ForeignKey(
        PayPeriod,
        on_delete=models.PROTECT,
        related_name='payslips',
    )
    basic_pay = models.DecimalField(max_digits=12, decimal_places=2)
    allowances_total = models.DecimalField(max_digits=12, decimal_places=2)
    late_deduction_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Total late deduction for the period"
    )
    absent_deduction_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Total absence deduction for the period"
    )
    holiday_pay_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Total additional holiday pay for the period"
    )
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    undertime_deduction_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Total undertime deduction for the period"
    )
    sss_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    philhealth_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pagibig_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    overtime_regular_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
    help_text="Overtime pay for ordinary working days")
    overtime_special_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
    help_text="Overtime pay for rest days, special non‑working holidays, regular holidays, etc.")
    absence_count = models.PositiveIntegerField(default=0)
    absence_dates = models.JSONField(blank=True, null=True, help_text="List of absence dates")
    leave_count = models.PositiveIntegerField(default=0)
    leave_dates = models.JSONField(blank=True, null=True, help_text="List of leave dates")
    nsd_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
    help_text="Total Night Shift Differential for the period")
    remaining_leave_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    rest_day_premium_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
    help_text="Total rest day premium for the period")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['employee', 'pay_period']
        ordering = ['employee__last_name', 'employee__first_name']

    def __str__(self):
        return f"Payslip: {self.employee} – {self.pay_period}"


class PayslipDailyDetail(models.Model):
    class DayStatus(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        LATE = 'LATE', 'Late'
        ABSENT = 'ABSENT', 'Absent'
        HOLIDAY = 'HOLIDAY', 'Holiday'
        REST_DAY = 'REST_DAY', 'Rest Day'

    payslip = models.ForeignKey(
        Payslip,
        on_delete=models.CASCADE,
        related_name='daily_details'
    )
    date = models.DateField()
    working_day = models.BooleanField(default=True)
    status = models.CharField(
        max_length=15,
        choices=DayStatus.choices,
        default=DayStatus.PRESENT,
    )
    late_minutes = models.PositiveIntegerField(default=0)
    late_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    absent_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    remarks = models.TextField(blank=True)
    undertime_minutes = models.PositiveIntegerField(default=0)
    undertime_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)        
    holiday = models.CharField(max_length=100, blank=True, null=True,
        help_text="Holiday name if applicable, e.g., 'Independence Day'")
    holiday_type = models.CharField(max_length=30, blank=True, null=True,
        help_text="e.g., REGULAR, SPECIAL_NON_WORKING")
    holiday_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    leave_type_name = models.CharField(max_length=100, blank=True, null=True,
    help_text="e.g., Vacation Leave, Sick Leave, if the day was an approved leave")
    overtime_minutes = models.PositiveIntegerField(default=0)
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)   
    overtime_type = models.CharField(max_length=30, blank=True, null=True,
    help_text="e.g., ORDINARY, REST_DAY, REGULAR_HOLIDAY")
    rest_day_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
    help_text="Rest day premium for this day")
    night_shift_diff = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
    help_text="NSD pay for this day")

    class Meta:
        ordering = ['date']
        unique_together = ['payslip', 'date']

    def __str__(self):
        return f"{self.payslip} – {self.date} ({self.status})"

class PayslipAdjustment(models.Model):
    payslip = models.ForeignKey(
        Payslip,
        on_delete=models.CASCADE,
        related_name='adjustments'
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Negative = deduction (e.g., loan), positive = addition (e.g., bonus)"
    )
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payslip} – {self.reason} ({self.amount})"

class SSSContribution(models.Model):
    """SSS monthly salary credit and employee share (2026)."""
    salary_from = models.DecimalField(max_digits=10, decimal_places=2)
    salary_to = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_salary_credit = models.DecimalField(max_digits=10, decimal_places=2)
    employee_share = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['salary_from']

    def __str__(self):
        return f"SSS {self.salary_from}-{self.salary_to}: {self.employee_share}"


class PhilHealthContribution(models.Model):
    """PhilHealth premium rates (2026)."""
    salary_from = models.DecimalField(max_digits=10, decimal_places=2)
    salary_to = models.DecimalField(max_digits=10, decimal_places=2)
    premium_rate = models.DecimalField(max_digits=5, decimal_places=4)
    employee_share_rate = models.DecimalField(max_digits=5, decimal_places=4)

    class Meta:
        ordering = ['salary_from']

    def __str__(self):
        return f"PhilHealth {self.salary_from}-{self.salary_to}"


class PagIBIGContribution(models.Model):
    """Pag‑IBIG employee contribution (2026)."""
    salary_from = models.DecimalField(max_digits=10, decimal_places=2)
    salary_to = models.DecimalField(max_digits=10, decimal_places=2)
    employee_share = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['salary_from']

    def __str__(self):
        return f"Pag‑IBIG {self.salary_from}-{self.salary_to}: {self.employee_share}"


class WithholdingTaxTable(models.Model):
    """BIR graduated withholding tax table (semi‑monthly, S/0)."""
    compensation_from = models.DecimalField(max_digits=10, decimal_places=2)
    compensation_to = models.DecimalField(max_digits=10, decimal_places=2)
    base_tax = models.DecimalField(max_digits=10, decimal_places=2)
    rate_above = models.DecimalField(max_digits=5, decimal_places=4)
    exemption_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['compensation_from']

    def __str__(self):
        return f"Tax {self.compensation_from}-{self.compensation_to}"


class CompanySettings(models.Model):
    company_name = models.CharField(max_length=200, default="PHILIPPINE HOME PHARMACEUTICAL")
    logo = models.ImageField(upload_to='company/', blank=True, null=True)

    def save(self, *args, **kwargs):
        self.pk = 1   # force a single record
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.company_name