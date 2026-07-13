from django.contrib import admin
from .models import (
    LeaveConfiguration, LeaveType, LeaveGrant, LeaveRequest, LeaveAdjustment
)

@admin.register(LeaveConfiguration)
class LeaveConfigurationAdmin(admin.ModelAdmin):
    list_display = ['annual_leave_days']

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'counts_towards_balance']

@admin.register(LeaveGrant)
class LeaveGrantAdmin(admin.ModelAdmin):
    list_display = ['employee', 'granted_days', 'year', 'credited_on', 'expires_on']

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status']
    list_filter = ['status', 'leave_type']

@admin.register(LeaveAdjustment)
class LeaveAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'reason']