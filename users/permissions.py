from rest_framework.permissions import BasePermission

def _has_profile_flag(user, flag_name):
    """Return True if user is HRADMIN or has the given profile flag.
    Returns False for anonymous users or users without a Profile."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'profile', None)
    if not profile:
        return False
    return profile.role == 'HRADMIN' or getattr(profile, flag_name, False)

class IsHRAdmin(BasePermission):
    message = "Only HR Administrators can perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        profile = getattr(user, 'profile', None)
        return bool(profile and profile.role == 'HRADMIN')

class CanManageLeave(BasePermission):
    message = "You do not have permission to approve/reject/cancel leave."

    def has_permission(self, request, view):
        return _has_profile_flag(request.user, 'can_manage_leave')

class CanManageOvertime(BasePermission):
    message = "You do not have permission to approve/reject/cancel overtime."

    def has_permission(self, request, view):
        return _has_profile_flag(request.user, 'can_manage_overtime')

class CanManageEmployees(BasePermission):
    message = "You do not have permission to manage employees."

    def has_permission(self, request, view):
        return _has_profile_flag(request.user, 'can_manage_employees')

class CanDeleteRecords(BasePermission):
    message = "You do not have permission to delete records."

    def has_permission(self, request, view):
        return _has_profile_flag(request.user, 'can_delete_records')

class CanLockPayroll(BasePermission):
    message = "You do not have permission to lock/unlock payroll."

    def has_permission(self, request, view):
        return _has_profile_flag(request.user, 'can_lock_payroll')

class CanManageLeaveAdjustments(BasePermission):
    message = "You do not have permission to manage leave adjustments."

    def has_permission(self, request, view):
        return _has_profile_flag(request.user, 'can_manage_leave_adjustments')

class CanImportAttendance(BasePermission):
    message = "You do not have permission to import attendance."

    def has_permission(self, request, view):
        return _has_profile_flag(request.user, 'can_import_attendance')

class CanManageLoans(BasePermission):
    message = "You do not have permission to manage loans."

    def has_permission(self, request, view):
        return _has_profile_flag(request.user, 'can_manage_loans')