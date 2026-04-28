from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
import logging

# Create a logger for this module – helps with debugging
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# CurrentUserSerializer
# Purpose: Serializes data about the currently authenticated user,
# enriched with information from their linked Employee profile.
# Used by the /api/me/ endpoint.
# ------------------------------------------------------------------
class CurrentUserSerializer(serializers.ModelSerializer):
    # These fields are not directly on the User model; they come from
    # the related Employee object. We use SerializerMethodField to
    # compute their values.
    full_name = serializers.SerializerMethodField()
    company_id = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = User
        # Only expose the fields a user needs to see about themselves.
        # No sensitive data like password or email is included here.
        fields = [
            'id',
            'username',
            'full_name',
            'company_id',
            'job_title',
            'department',
        ]

    # ---------------------------------------------------------------
    # Helper: Safely retrieve the Employee linked to this user.
    # Returns an Employee instance or None if something is missing.
    # Logs warnings for expected missing data, and full errors for
    # unexpected bugs.
    # ---------------------------------------------------------------
    def _get_employee(self, obj):
        try:
            # Navigate from User -> Profile -> Employee
            return obj.profile.employee
        except (ObjectDoesNotExist, AttributeError) as e:
            # These exceptions mean the Profile or Employee is missing.
            # This is not a code bug – just a user who hasn't been
            # fully linked yet. Log as a warning and return None.
            logger.warning(f"Could not retrieve employee for user {obj.username}: {e}")
            return None
        except Exception as e:
            # Any other error is unexpected (e.g., database error).
            # Log the full traceback so we can investigate.
            logger.exception(f"Unexpected error retrieving employee for {obj.username}")
            return None

    # ---------------------------------------------------------------
    # Field methods – each computes one value for the response.
    # All follow the same pattern:
    # 1. Get the employee (or None)
    # 2. Safely access the desired attribute
    # 3. Return the value or None if not available
    # ---------------------------------------------------------------

    def get_full_name(self, obj):
        employee = self._get_employee(obj)
        if employee:
            return f"{employee.first_name} {employee.last_name}"
        return None

    def get_company_id(self, obj):
        employee = self._get_employee(obj)
        # company_id is a direct field on Employee – safe to access
        return employee.company_id if employee else None

    def get_job_title(self, obj):
        employee = self._get_employee(obj)
        if not employee:
            return None
        try:
            # employee.job_title might be None if no job title is assigned.
            # Accessing .title on None would raise AttributeError.
            return employee.job_title.title
        except AttributeError:
            # Perfectly normal – no job title assigned.
            return None

    def get_department(self, obj):
        employee = self._get_employee(obj)
        if not employee:
            return None
        try:
            # Same logic: employee.department can be None.
            return employee.department.name
        except AttributeError:
            return None


# ------------------------------------------------------------------
# ChangePasswordSerializer
# Purpose: Validates password change requests. Ensures the old
# password is correct, new passwords match and are different,
# and meets Django's built-in password strength requirements.
# Does NOT save anything – that's the view's job.
# ------------------------------------------------------------------
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]  # Django's AUTH_PASSWORD_VALIDATORS
    )
    confirm_new_password = serializers.CharField(required=True)

    # ---------------------------------------------------------------
    # Validate the old password against the current user's stored
    # password. The user is taken from the request context.
    # ---------------------------------------------------------------
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    # ---------------------------------------------------------------
    # Cross-field validation: new passwords must match and cannot
    # be the same as the old one.
    # ---------------------------------------------------------------
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