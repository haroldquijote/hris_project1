from rest_framework import serializers
from .models import EmployeeLoan, LoanPayment


class LoanPaymentSerializer(serializers.ModelSerializer):
    pay_period_label = serializers.SerializerMethodField()

    class Meta:
        model = LoanPayment
        fields = [
            'id', 'pay_period', 'pay_period_label', 'payslip',
            'amount', 'balance_before', 'balance_after',
            'reversed_at', 'created_at',
        ]
        read_only_fields = fields

    def get_pay_period_label(self, obj):
        p = obj.pay_period
        return f"{p.start_date.strftime('%b %d')} – {p.end_date.strftime('%b %d, %Y')}"


class EmployeeLoanSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    company_id = serializers.CharField(source='employee.company_id', read_only=True)
    display_name = serializers.CharField(read_only=True)
    monthly_amortization = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    per_period_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    total_periods = serializers.IntegerField(read_only=True)
    months_paid = serializers.IntegerField(read_only=True)
    months_remaining = serializers.IntegerField(read_only=True)
    progress_percent = serializers.FloatField(read_only=True)
    next_payment = serializers.SerializerMethodField()
    payments = LoanPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeLoan
        fields = [
            'id', 'employee', 'employee_name', 'company_id',
            'loan_type', 'custom_name', 'display_name',
            'principal_amount', 'months_to_pay',
            'monthly_amortization', 'per_period_amount', 'total_periods',
            'balance', 'periods_paid', 'months_paid', 'months_remaining',
            'progress_percent', 'start_date', 'status',
            'next_payment', 'payments',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'balance', 'periods_paid',
            'monthly_amortization', 'per_period_amount', 'total_periods',
            'months_paid', 'months_remaining', 'progress_percent',
            'display_name', 'payments', 'created_at', 'updated_at',
        ]

    def get_next_payment(self, obj):
        return str(obj.calculate_next_payment())

    def validate(self, data):
        loan_type = data.get('loan_type')
        custom_name = data.get('custom_name')
        if loan_type == EmployeeLoan.LoanType.OTHER and not custom_name:
            raise serializers.ValidationError(
                {'custom_name': 'Custom name is required when loan_type is OTHER.'}
            )
        if data.get('months_to_pay', 0) < 1:
            raise serializers.ValidationError(
                {'months_to_pay': 'Must be at least 1 month.'}
            )
        if data.get('principal_amount', 0) <= 0:
            raise serializers.ValidationError(
                {'principal_amount': 'Must be greater than 0.'}
            )
        return data