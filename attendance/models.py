from django.db import models


class Attendance(models.Model):
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="attendances",
    )
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    is_manual_entry = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.date}"

    class Meta:
        ordering = ["-date"]
        unique_together = ["employee", "date"]

# OvertimeRequest model to handle employee overtime requests and approvals
class OvertimeRequest(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    OVERTIME_TYPE_CHOICES = [
    ('REGULAR', 'Regular Overtime'),
    ('REST_DAY', 'Rest Day'),
    ('SPECIAL_HOLIDAY', 'Special Holiday'),
    ('REGULAR_HOLIDAY', 'Regular Holiday'),

    ]

    # Core Fields
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="overtime_requests"
    )
    date = models.DateField()
    overtime_type = models.CharField(
        max_length=20,
        choices=OVERTIME_TYPE_CHOICES,
        default='REGULAR'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    # Request Details
    requested_start_time = models.TimeField()
    requested_end_time = models.TimeField()
    reason = models.TextField()

    # Filing Details
    filed_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="overtime_filed",
        null=True,
        blank=True
    )

    # Approval Details 
    approved_by = models.CharField(max_length=200, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Actual Overtime
    actual_end_time = models.TimeField(null=True, blank=True)
    colleague_reference = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="overtime_references",
        null=True,
        blank=True
    )

    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.date} - {self.overtime_type}"

    class Meta:
        ordering = ["-date"]
  
 # BiometricMapping model to link biometric numbers to employees       
class BiometricMapping(models.Model):
    biometric_number = models.PositiveIntegerField(unique=True)
    employee = models.OneToOneField(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="biometric_mapping"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.biometric_number} - {self.employee}"

    class Meta:
        ordering = ["biometric_number"]