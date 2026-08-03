from django.contrib import admin
from .models import OvertimeRequest, OvertimeConfiguration

@admin.register(OvertimeRequest)
class OvertimeRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'start_time', 'end_time', 'overtime_hours', 'status']
    list_filter = ['status', 'date']

@admin.register(OvertimeConfiguration)
class OvertimeConfigurationAdmin(admin.ModelAdmin):
    pass