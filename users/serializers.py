from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
import logging

logger = logging.getLogger(__name__)


class CurrentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    company_id = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'full_name',
            'company_id',
            'job_title',
            'department',
        ]

    def _get_employee(self, obj):
        try:
            return obj.profile.employee
        except Exception as e:
            logger.warning(f"Could not retrieve employee for user {obj.username}: {e}")
            return None

    def get_full_name(self, obj):
        employee = self._get_employee(obj)
        if employee:
            return f"{employee.first_name} {employee.last_name}"
        return None

    def get_company_id(self, obj):
        employee = self._get_employee(obj)
        return employee.company_id if employee else None

    def get_job_title(self, obj):
        employee = self._get_employee(obj)
        try:
            return employee.job_title.title if employee else None
        except Exception:
            return None

    def get_department(self, obj):
        employee = self._get_employee(obj)
        try:
            return employee.department.name if employee else None
        except Exception:
            return None


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )
    confirm_new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({
                "confirm_new_password": "New passwords do not match."
            })
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({
                "new_password": "New password cannot be the same as old password."
            })
        return data