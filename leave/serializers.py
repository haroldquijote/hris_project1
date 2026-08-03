from rest_framework import serializers
from datetime import date
from .models import (
    LeaveType, LeaveGrant, LeaveRequest, LeaveAdjustment, LeaveConfiguration
)
from .utils import get_balance, get_used_days   # we'll create this next
from employees.models import Employee


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'description', 'counts_towards_balance',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaveGrantSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = LeaveGrant
        fields = ['id', 'employee', 'employee_name', 'granted_days',
                  'year', 'credited_on', 'expires_on', 'created_at']
        read_only_fields = ['id', 'created_at']


class LeaveAdjustmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = LeaveAdjustment
        fields = ['id', 'employee', 'employee_name', 'amount', 'reason',
                  'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name',
            'leave_type', 'leave_type_name', 'custom_leave_type',
            'start_date', 'end_date', 'reason', 'status',
            'reviewed_by', 'reviewed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at']

    def validate(self, data):
        # Basic date validation
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be before end date.")

        # For creation: status default is PENDING, no extra checks.
        # For updates: status transitions handled in views.
        return data


class LeaveRequestApproveSerializer(serializers.Serializer):
    """Used only for approving a request (no other fields)."""
    status = serializers.ChoiceField(choices=['APPROVED'], required=False)

    def validate(self, data):
        request = self.context['request_obj']
        if request.status != LeaveRequest.Status.PENDING:
            raise serializers.ValidationError("Only pending requests can be approved.")
        # Balance check (only for counted types)
        if request.leave_type.counts_towards_balance:
            balance = get_balance(request.employee)
            if balance < request.total_days():
                raise serializers.ValidationError(
                    f"Insufficient balance. {request.employee.full_name} has only "
                    f"{balance} day(s) remaining."
                )
        return data


class LeaveRequestRejectSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['REJECTED'], required=False)

    def validate(self, data):
        request = self.context['request_obj']
        if request.status != LeaveRequest.Status.PENDING:
            raise serializers.ValidationError("Only pending requests can be rejected.")
        return data


class LeaveRequestCancelSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['CANCELED'], required=False)

    def validate(self, data):
        request = self.context['request_obj']
        if request.status != LeaveRequest.Status.APPROVED:
            raise serializers.ValidationError("Only approved requests can be cancelled.")
        return data