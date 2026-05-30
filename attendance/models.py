from django.db import models


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        LATE = 'LATE', 'Late'
        ABSENT = 'ABSENT', 'Absent'
        HALF_DAY = 'HALF_DAY', 'Half Day'
        UNDERTIME = 'UNDERTIME', 'Undertime'

    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.PROTECT,
        related_name='attendance_records'
    )
    date = models.DateField()
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    is_manual = models.BooleanField(default=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ['employee', 'date']

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"


class WorkSchedule(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_monday = models.BooleanField(default=False)
    is_tuesday = models.BooleanField(default=False)
    is_wednesday = models.BooleanField(default=False)
    is_thursday = models.BooleanField(default=False)
    is_friday = models.BooleanField(default=False)
    is_saturday = models.BooleanField(default=False)
    is_sunday = models.BooleanField(default=False)
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    grace_period_minutes = models.PositiveIntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']