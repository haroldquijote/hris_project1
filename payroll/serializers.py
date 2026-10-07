from rest_framework import serializers
from .models import PayPeriod, Payslip, PayslipDailyDetail, PayslipAdjustment


def _user_display_name(user):
    """Return full name if available, otherwise username. None if user is None."""
    if not user:
        return None
    full = user.get_full_name().strip()
    return full if full else user.username


class PayPeriodSerializer(serializers.ModelSerializer):
    locked_by_name   = serializers.SerializerMethodField()
    unlocked_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PayPeriod
        fields = [
            'id', 'start_date', 'end_date', 'status', 'period_type',
            'locked_by', 'locked_by_name','locked_at', 'unlocked_by', 'unlocked_by_name', 'unlocked_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'locked_by', 'locked_by_name', 'locked_at', 'unlocked_by','unlocked_by_name',  'unlocked_at',
        ]

    def get_locked_by_name(self, obj):
        return _user_display_name(obj.locked_by)

    def get_unlocked_by_name(self, obj):
        return _user_display_name(obj.unlocked_by)

class PayPeriodMiniSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = PayPeriod
        fields = ['id', 'start_date', 'end_date', 'period_type', 'status', 'label']

    def get_label(self, obj):
        start = obj.start_date.strftime('%b %d').replace(' 0', ' ')
        end = obj.end_date.strftime('%b %d, %Y').replace(' 0', ' ')
        return f"{start} – {end}"

class PayslipDailyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipDailyDetail
        fields = [
            'id', 'date', 'working_day', 'status','absent_deduction',
            'late_minutes', 'late_deduction', 'undertime_minutes','undertime_deduction',  'overtime_pay', 'overtime_type', 'night_shift_diff', 
            'overtime_minutes', 'holiday' , 'holiday_type' ,'holiday_extra', 'remarks', 'leave_type_name',
        ]


class PayslipAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipAdjustment
        fields = ['id', 'payslip', 'amount', 'reason', 'created_at']
        read_only_fields = ['id', 'created_at']

class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    daily_details = PayslipDailyDetailSerializer(many=True, read_only=True) 
    adjustments = PayslipAdjustmentSerializer(many=True, read_only=True)
    job_title_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    allowance_breakdown = serializers.SerializerMethodField()
    daily_rate = serializers.SerializerMethodField()
    pay_period = PayPeriodMiniSerializer(read_only=True)

    class Meta:
        model = Payslip
        fields = [
            'id', 'employee', 'employee_name','job_title_name', 'department_name', 'pay_period',
            'basic_pay','daily_rate','allowance_breakdown', 'allowances_total',
            'late_deduction_total', 'absent_deduction_total',
            'undertime_deduction_total', 'holiday_pay_total',
            'overtime_pay', 'overtime_regular_pay', 'overtime_special_pay','nsd_total','rest_day_premium_total', 
            'gross_pay',
            'sss_deduction', 'philhealth_deduction', 'pagibig_deduction',
            'tax_deduction', 'adjustments','net_pay',
            'absence_count', 'absence_dates', 'leave_count', 'leave_dates',
            'remaining_leave_balance',
            'status', 'created_at', 'updated_at',
            'daily_details', 
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'daily_details',
            'late_deduction_total', 'absent_deduction_total',
            'undertime_deduction_total', 'holiday_pay_total','overtime_pay','overtime_regular_pay', 'overtime_special_pay', 
            'sss_deduction', 'philhealth_deduction', 'pagibig_deduction',
            'tax_deduction', 'net_pay','pay_period','adjustments','absence_count', 'absence_dates', 'leave_count', 'leave_dates',
            'remaining_leave_balance','job_title_name','department_name','nsd_total',
            'allowance_breakdown','daily_rate','rest_day_premium_total',    
        ]
    def get_daily_rate(self, obj):
        employee = obj.employee
        # Get active monthly salary
        from employees.models import EmployeeSalary
        active_salary = EmployeeSalary.objects.filter(
            employee=employee, end_date__isnull=True
        ).first()
        if not active_salary:
            return None
        # 365‑day factor: daily rate = (monthly * 12) / 365
        return round((active_salary.base_salary * 12) / 365, 2)
    
    def get_job_title_name(self, obj):
        employee = obj.employee
        if employee and employee.job_title:
            return employee.job_title.title
        return None

    def get_department_name(self, obj):
        employee = obj.employee
        if employee and employee.department:
            return employee.department.name
        return None

    def get_allowance_breakdown(self, obj):
        from employees.models import EmployeeAllowance
        import calendar
        from decimal import Decimal

        # If the payslip's total allowance was clamped to zero
        # (e.g., full-period absence), the breakdown should be empty too.
        if not obj.allowances_total or Decimal(obj.allowances_total) == 0:
            return []

        allowances = EmployeeAllowance.objects.filter(
            employee=obj.employee,
            end_date__isnull=True
        )
        if not allowances or not obj.pay_period:
            return []

        pay_period = obj.pay_period
        year = pay_period.start_date.year
        month = pay_period.start_date.month
        days_in_month = calendar.monthrange(year, month)[1]
        days_in_period = (pay_period.end_date - pay_period.start_date).days + 1

        # Detect standard semi-monthly period (same rule as compute_phase2_gross_pay)
        is_first_half = pay_period.start_date.day == 1 and pay_period.end_date.day == 15
        is_second_half = pay_period.start_date.day == 16 and pay_period.end_date.day == days_in_month
        is_standard = is_first_half or is_second_half

        breakdown = []
        for a in allowances:
            monthly_amount = Decimal(str(a.amount))
            if is_standard:
                prorated = round(monthly_amount / 2, 2)
            else:
                prorated = round((monthly_amount / days_in_month) * days_in_period, 2)
            breakdown.append({
                'allowance_type': a.allowance_type.name,
                'monthly_amount': str(monthly_amount),
                'prorated_amount': str(prorated),
            })
        return breakdown
    
