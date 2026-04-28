from rest_framework import serializers
from .models import Employee, Department, JobTitle, WorkSchedule, EmployeeSalary


# ================================================================
# Nested / Supporting Serializers
# ================================================================

class DepartmentSerializer(serializers.ModelSerializer):
    """Used to read / write department data. Also nested inside Employee response."""
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class JobTitleSerializer(serializers.ModelSerializer):
    """
    Used for JobTitle CRUD.
    The `department_name` field shows the department's name without needing
    an extra query (dot‑notation is safe here because Department is always required).
    """
    department_name = serializers.CharField(
        source='department.name',
        read_only=True
    )

    class Meta:
        model = JobTitle
        fields = ['id', 'title', 'department', 'department_name',
                  'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ---------------------------------------------------------------
# IMPROVEMENT ① : WorkScheduleSerializer now exposes ALL model fields.
# Previously it only had 'id', 'name', 'shift_start', 'shift_end'.
# The missing fields meant you couldn't set working days or the grace period.
# ---------------------------------------------------------------
class WorkScheduleSerializer(serializers.ModelSerializer):
    """Used to read / write work schedules. Now includes all schedule configuration."""
    class Meta:
        model = WorkSchedule
        fields = [
            'id',
            'name',
            # Working days – each is a simple BooleanField
            'is_monday', 'is_tuesday', 'is_wednesday',
            'is_thursday', 'is_friday', 'is_saturday', 'is_sunday',
            # Shift timing
            'shift_start',
            'shift_end',
            'grace_period_minutes',
            # Metadata (read‑only)
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ================================================================
# Employee Serializers
# ================================================================

class EmployeeSerializer(serializers.ModelSerializer):
    """Main serializer for Employee CRUD operations."""

    # Read‑only nested representations – they show the full related object data.
    department_detail = DepartmentSerializer(source='department', read_only=True)
    job_title_detail = JobTitleSerializer(source='job_title', read_only=True)
    work_schedule_detail = WorkScheduleSerializer(source='work_schedule', read_only=True)

    # Full name is computed, never stored.
    full_name = serializers.SerializerMethodField()

    # ---------------------------------------------------------------
    # IMPROVEMENT ② : Use Django’s built-in `get_FOO_display()` for choice fields.
    # Before: manual dict lookup like `dict(Employee.EMPLOYMENT_STATUS).get(...)`.
    # Now: cleaner, always matches model choices, one line.
    # ---------------------------------------------------------------
    employment_status_display = serializers.CharField(
        source='get_employment_status_display', read_only=True
    )
    gender_display = serializers.CharField(
        source='get_gender_display', read_only=True
    )
    marital_status_display = serializers.CharField(
        source='get_marital_status_display', read_only=True
    )

    class Meta:
        model = Employee
        fields = [
            'id',
            'company_id',
            # FK IDs (for writing)
            'department',
            'job_title',
            'work_schedule',
            # FK detailed representations (read‑only)
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
        return f"{obj.first_name} {obj.last_name}"


class EmployeeListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing employees.
    Uses only essential fields to keep response fast.
    """
    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    job_title_name = serializers.CharField(source='job_title.title', read_only=True)

    # Also use the built‑in display method
    employment_status_display = serializers.CharField(
        source='get_employment_status_display', read_only=True
    )

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


# ================================================================
# Employee Salary Serializers
# ================================================================

class EmployeeSalarySerializer(serializers.ModelSerializer):
    """Read‑only serializer for salary records with extra display fields."""

    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)

    # Check if this salary is the current one (no end_date)
    is_current = serializers.BooleanField(read_only=True)

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
        read_only_fields = [
            'id', 'created_by', 'created_at', 'approved_by', 'approved_at', 'is_current'
        ]

    def get_is_current(self, obj):
        # Override the BooleanField source – we keep a method for clarity
        return obj.end_date is None


class EmployeeSalaryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer used purely for creating / updating salary records.
    Excludes audit fields (created_by, approved_by) – those are handled by the view.
    """

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
        """Ensure end_date is after effective_date if provided."""
        if data.get('end_date') and data.get('effective_date'):
            if data['end_date'] <= data['effective_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after effective date'
                })
        return data