from django.contrib import admin
from .models import AttendanceRecord, WorkSchedule

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'clock_in', 'clock_out', 'status', 'is_manual']
    list_filter = ['status', 'date', 'is_manual']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__company_id']

@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'shift_start', 'shift_end', 'grace_period_minutes']
    ordering = ['name']