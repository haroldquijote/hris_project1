from django.contrib import admin

from .models import Attendance, BiometricMapping, OvertimeRequest

# Register your models here. 
# Admin for BiometricMapping model to manage the mapping between biometric numbers and employees
@admin.register(BiometricMapping)
class BiometricMappingAdmin(admin.ModelAdmin):
    list_display = ("biometric_number", "employee", "created_at", "updated_at")
    search_fields = ("biometric_number", "employee__last_name", "employee__first_name", "employee__company_id")

# Admin for Attendance model to manage employee attendance records
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "time_in", "time_out", "is_manual_entry", "created_at", "updated_at")
    list_filter = ("date", "is_manual_entry")
    search_fields = ("employee__company_id", "employee__last_name", "employee__first_name")

# Admin for OvertimeRequest model to manage employee overtime requests and approvals
@admin.register(OvertimeRequest)
class OvertimeRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "overtime_type", "status", "filed_by", "approved_by", "created_at")
    list_filter = ("status", "overtime_type", "date")
    search_fields = ("employee__company_id", "employee__last_name", "employee__first_name")