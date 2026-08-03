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

    def validate(self, data):
        """
        Custom validation:
        1. clock_out must be after clock_in (if both are present).
        2. clock_in date must match the 'date' field.
        3. clock_out date must be the same or the next calendar day (overnight shift allowed).
        4. Friendly duplicate record error.
        """
        from datetime import timedelta

        clock_in = data.get('clock_in')
        clock_out = data.get('clock_out')
        record_date = data.get('date')

        # 1. Check order of clock in/out
        if clock_in and clock_out:
            if clock_out <= clock_in:
                raise serializers.ValidationError({
                    'clock_out': 'Clock‑out time must be after clock‑in time.'
                })

        # 2. Date consistency for clock-in
        if clock_in and record_date:
            if clock_in.date() != record_date:
                raise serializers.ValidationError({
                    'clock_in': 'Clock‑in date does not match the record date.'
                })

        # 3. Date consistency for clock-out (allow overnight shift)
        if clock_out and record_date:
            next_day = record_date + timedelta(days=1)
            if clock_out.date() not in (record_date, next_day):
                raise serializers.ValidationError({
                    'clock_out': 'Clock‑out date must be the same day or the next day.'
                })

        # 4. Friendly duplicate record check
        employee = data.get('employee')
        date = data.get('date')
        if employee and date:
            existing = AttendanceRecord.objects.filter(employee=employee, date=date)
            if self.instance:   # exclude current instance when updating
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({
                    'employee': f'A record for this employee on {date} already exists. Please update the existing record instead.'
                })

        return data


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