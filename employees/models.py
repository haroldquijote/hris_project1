from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    """Company department (e.g., HR, IT, Finance)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class JobTitle(models.Model):
    """Job title / position within a department."""
    title = models.CharField(max_length=200, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,       # Prevent deleting a department if job titles still exist
        related_name="job_titles",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]




class Employee(models.Model):
    """Employee master record with personal, employment, and government IDs."""

    EMPLOYMENT_STATUS = [
        ("REGULAR", "Regular"),
        ("PROBATIONARY", "Probationary"),
        ("CONTRACTUAL", "Contractual"),
        ("RESIGNED", "Resigned"),
        ("TERMINATED", "Terminated"),
    ]

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    MARITAL_CHOICES = [
        ("S", "Single"),
        ("M", "Married"),
        ("W", "Widowed"),
        ("D", "Divorced"),
    ]

    # Identity & employment
    company_id = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees",
    )
    job_title = models.ForeignKey(
        JobTitle,
        on_delete=models.PROTECT,
        related_name="employees",
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS,
        default="PROBATIONARY",
    )
    date_hired = models.DateField()
    date_of_resignation = models.DateField(null=True, blank=True)

    work_schedule = models.ForeignKey(
        'attendance.WorkSchedule',
        on_delete=models.PROTECT,
        related_name='employees',
        null=True,
        blank=True,
    )

    # Name
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    mothers_maiden_name = models.CharField(max_length=200, blank=True)

    # Personal details
    birth_date = models.DateField()
    birth_place = models.CharField(max_length=200)
    nationality = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=1, choices=MARITAL_CHOICES)

    # Address
    permanent_address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    mobile_no = models.CharField(max_length=20)
    email = models.EmailField(unique=True)

    # Government IDs
    tin = models.CharField(max_length=20, blank=True)
    sss_gsis_no = models.CharField(max_length=20, blank=True)
    hdmf = models.CharField(max_length=20, blank=True)
    philhealth = models.CharField(max_length=20, blank=True)
    drivers_license = models.CharField(max_length=20, blank=True)
    passport = models.CharField(max_length=20, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -----------------------------------------------------------------
    # CRITICAL FIX: The salary serializer references employee.full_name.
    # This property provides that attribute safely.
    # -----------------------------------------------------------------
    @property
    def full_name(self):
        """Returns the employee's full name in 'First Last' format."""
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    class Meta:
        ordering = ["last_name", "first_name"]

class AllowanceType(models.Model):
    """Master list of allowance names (e.g., Food, Transport, Housing)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class EmployeeAllowance(models.Model):
    """Assigns a specific allowance to an employee with an amount."""
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='allowances'
    )
    allowance_type = models.ForeignKey(
        AllowanceType,
        on_delete=models.PROTECT,
        related_name='employee_allowances'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} – {self.allowance_type} ({self.amount})"

    class Meta:
        ordering = ['-effective_date']
        verbose_name_plural = "Employee Allowances"


class EmployeeSalary(models.Model):
    """Salary history for an employee – supports effective dating."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='salaries',
    )

    # Compensation
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)

    # Effective dating
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)   # null = current salary

    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255)

    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee} - {self.base_salary} (effective {self.effective_date})"

    class Meta:
        ordering = ['-effective_date']
        verbose_name_plural = "Employee Salaries"