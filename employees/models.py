from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class JobTitle(models.Model):
    title = models.CharField(max_length=200, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="job_titles",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]

# Additional models for work schedules, leave types, etc. can be added here as needed.
class WorkSchedule(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    # Working Days
    is_monday = models.BooleanField(default=False)
    is_tuesday = models.BooleanField(default=False)
    is_wednesday = models.BooleanField(default=False)
    is_thursday = models.BooleanField(default=False)
    is_friday = models.BooleanField(default=False)
    is_saturday = models.BooleanField(default=False)
    is_sunday = models.BooleanField(default=False)
    
    # Shift Details
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    grace_period_minutes = models.PositiveIntegerField(default=15)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Employee(models.Model):
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
    WorkSchedule,
    on_delete=models.PROTECT,
    related_name='employees',
    null=True,
    blank=True
    )

    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    mothers_maiden_name = models.CharField(max_length=200, blank=True)
    birth_date = models.DateField()
    birth_place = models.CharField(max_length=200)
    nationality = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=1, choices=MARITAL_CHOICES)

    permanent_address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    mobile_no = models.CharField(max_length=20)
    email = models.EmailField(unique=True)

    tin = models.CharField(max_length=20, blank=True)
    sss_gsis_no = models.CharField(max_length=20, blank=True)
    hdmf = models.CharField(max_length=20, blank=True)
    philhealth = models.CharField(max_length=20, blank=True)
    drivers_license = models.CharField(max_length=20, blank=True)
    passport = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    class Meta:
        ordering = ["last_name", "first_name"]

class EmployeeSalary(models.Model):
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.PROTECT, 
        related_name='salaries'
    )
    
    # Salary components
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Effective dating
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Audit fields
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255)
    
    # Optional: approval workflow
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='+'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee} - {self.base_salary} (effective {self.effective_date})"

    class Meta:
        ordering = ['-effective_date']
        verbose_name_plural = "Employee Salaries"