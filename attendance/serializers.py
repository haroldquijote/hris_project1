from rest_framework import serializers
from .models import AttendanceRecord,  WorkSchedule


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source='employee.full_name', read_only=True
    )

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'employee', 'employee_name', 'date',
            'clock_in', 'clock_out', 'status', 'is_manual',
            'remarks', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_manual']


class WorkScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = [
            'id', 'name',
            'is_monday', 'is_tuesday', 'is_wednesday',
            'is_thursday', 'is_friday', 'is_saturday', 'is_sunday',
            'shift_start', 'shift_end', 'grace_period_minutes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']