from django.contrib import admin
from .models import Department, JobTitle, Employee, EmployeeSalary, AllowanceType, EmployeeAllowance


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']
    search_fields = ['name']
    list_display_links = ['name']


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'department']
    list_filter = ['department']
    search_fields = ['title']
    list_display_links = ['title']





@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_id', 'last_name', 'first_name', 'department', 'job_title', 'employment_status']
    list_filter = ['department', 'job_title', 'employment_status', 'gender']
    search_fields = ['company_id', 'first_name', 'last_name', 'email']
    list_display_links = ['company_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('company_id', 'first_name', 'last_name', 'middle_name', 'email', 'mobile_no')
        }),
        ('Employment', {
            'fields': ('department', 'job_title', 'work_schedule', 'employment_status', 'date_hired', 'date_of_resignation')
        }),
        ('Personal Information', {
            'fields': ('birth_date', 'birth_place', 'gender', 'marital_status', 'nationality')
        }),
        ('Address', {
            'fields': ('permanent_address', 'city', 'zip_code')
        }),
        ('Government IDs', {
            'fields': ('tin', 'sss_gsis_no', 'hdmf', 'philhealth', 'drivers_license', 'passport')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
    list_display = ['id', 'employee', 'base_salary', 'effective_date', 'is_current', 'reason']
    list_filter = ['effective_date', 'created_at']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__company_id']
    readonly_fields = ['created_by', 'created_at', 'approved_by', 'approved_at']
    
    def is_current(self, obj):
        return obj.end_date is None
    is_current.boolean = True  # Shows as icon instead of True/False
    is_current.short_description = 'Current'
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by when creating new salary record"""
        if not obj.pk:  # If new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(AllowanceType)
class AllowanceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at', 'updated_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(EmployeeAllowance)
class EmployeeAllowanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'allowance_type', 'amount', 'effective_date', 'end_date', 'created_at']
    list_filter = ['allowance_type', 'effective_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'allowance_type__name']
    ordering = ['-effective_date']