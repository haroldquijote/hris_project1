from rest_framework import serializers
from .models import Employee, Department, JobTitle, WorkSchedule, EmployeeSalary


# ---------- Nested Serializers (for read-only details) ----------

class DepartmentSerializer(serializers.ModelSerializer):
    """Used to show department details inside Employee response"""
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class JobTitleSerializer(serializers.ModelSerializer):
    """Used to show job title details inside Employee response"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    class Meta:
        model = JobTitle
        fields = ['id', 'title', 'department', 'department_name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkScheduleSerializer(serializers.ModelSerializer):
    """Used to show work schedule inside Employee response"""
    class Meta:
        model = WorkSchedule
        fields = ['id', 'name', 'shift_start', 'shift_end']


# ---------- Main Employee Serializer (Create/Update/List) ----------

class EmployeeSerializer(serializers.ModelSerializer):
    """Main serializer for Employee CRUD operations"""
    
    # Read-only nested fields (show related object details)
    department_detail = DepartmentSerializer(source='department', read_only=True)
    job_title_detail = JobTitleSerializer(source='job_title', read_only=True)
    work_schedule_detail = WorkScheduleSerializer(source='work_schedule', read_only=True)
    
    # Human-readable display fields
    full_name = serializers.SerializerMethodField()
    employment_status_display = serializers.SerializerMethodField()
    gender_display = serializers.SerializerMethodField()
    marital_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id',
            'company_id',
            # Related objects (IDs for writing)
            'department',
            'job_title',
            'work_schedule',
            # Related objects (details for reading)
            'department_detail',
            'job_title_detail',
            'work_schedule_detail',
            # Basic info
            'last_name',
            'first_name',
            'middle_name',
            'full_name',
            'email',
            'mobile_no',
            # Employment
            'employment_status',
            'employment_status_display',
            'date_hired',
            'date_of_resignation',
            # Personal
            'birth_date',
            'birth_place',
            'gender',
            'gender_display',
            'marital_status',
            'marital_status_display',
            'nationality',
            # Address
            'permanent_address',
            'city',
            'zip_code',
            # Government IDs
            'tin',
            'sss_gsis_no',
            'hdmf',
            'philhealth',
            'drivers_license',
            'passport',
            # Metadata
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        """Return full name: First Last"""
        return f"{obj.first_name} {obj.last_name}"
    
    def get_employment_status_display(self, obj):
        """Return human-readable employment status"""
        return dict(Employee.EMPLOYMENT_STATUS).get(obj.employment_status, obj.employment_status)
    
    def get_gender_display(self, obj):
        """Return human-readable gender"""
        return dict(Employee.GENDER_CHOICES).get(obj.gender, obj.gender)
    
    def get_marital_status_display(self, obj):
        """Return human-readable marital status"""
        return dict(Employee.MARITAL_CHOICES).get(obj.marital_status, obj.marital_status)


# ---------- List Serializer (Lighter version for listing many employees) ----------

class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing employees (excludes sensitive/verbose fields)"""
    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    job_title_name = serializers.CharField(source='job_title.title', read_only=True)
    employment_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id',
            'company_id',
            'full_name',
            'email',
            'department_name',
            'job_title_name',
            'employment_status',
            'employment_status_display',
            'date_hired',
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_employment_status_display(self, obj):
        return dict(Employee.EMPLOYMENT_STATUS).get(obj.employment_status, obj.employment_status)


# ---------- Employee Salary Serializer ----------

class EmployeeSalarySerializer(serializers.ModelSerializer):
    """Serializer for Employee Salary (production-ready)"""
    
    # Read-only fields for display
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    
    # Human-readable display
    is_current = serializers.SerializerMethodField()
    
    class Meta:
        model = EmployeeSalary
        fields = [
            'id',
            'employee',
            'employee_name',
            'base_salary',
            'monthly_allowance',
            'effective_date',
            'end_date',
            'is_current',
            'reason',
            'created_by',
            'created_by_name',
            'created_at',
            'approved_by',
            'approved_by_name',
            'approved_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'approved_by', 'approved_at']
    
    def get_is_current(self, obj):
        """Return True if this is the current active salary"""
        return obj.end_date is None


# ---------- Create/Update Salary Serializer (Separate for write operations) ----------

class EmployeeSalaryCreateSerializer(serializers.ModelSerializer):
    """Serializer specifically for creating/updating salary records"""
    
    class Meta:
        model = EmployeeSalary
        fields = [
            'employee',
            'base_salary',
            'monthly_allowance',
            'effective_date',
            'end_date',
            'reason',
        ]
    
    def validate(self, data):
        """Custom validation for salary records"""
        # Ensure effective_date is not in the past? (Optional)
        # from datetime import date
        # if data['effective_date'] < date.today():
        #     raise serializers.ValidationError("Effective date cannot be in the past")
        
        # Ensure end_date is after effective_date if provided
        if data.get('end_date') and data['end_date'] <= data['effective_date']:
            raise serializers.ValidationError({
                'end_date': 'End date must be after effective date'
            })
        
        return data