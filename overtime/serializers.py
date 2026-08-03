from rest_framework import serializers
from .models import OvertimeRequest, OvertimeConfiguration


class OvertimeRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = OvertimeRequest
        fields = [
            'id', 'employee', 'employee_name', 'date',
            'start_time', 'end_time', 'overtime_hours',
            'status', 'approved_by', 'approved_at',
            'reason', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'approved_by', 'approved_at']


class OvertimeConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OvertimeConfiguration
        fields = [
            'ordinary_day_multiplier', 'rest_day_multiplier',
            'special_non_working_holiday_multiplier',
            'special_day_on_rest_day_multiplier',
            'regular_holiday_multiplier',
            'regular_holiday_on_rest_day_multiplier',
            'rest_day_first8_multiplier',
            'special_non_working_first8_multiplier',
            'special_on_rest_day_first8_multiplier',
            'regular_holiday_first8_multiplier',
            'regular_on_rest_day_first8_multiplier',
        ]