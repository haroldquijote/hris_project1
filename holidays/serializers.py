from rest_framework import serializers
from .models import Holiday


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = [
            'id', 'name', 'date', 'holiday_type',
            'percentage', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']