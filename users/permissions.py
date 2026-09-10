from rest_framework.permissions import BasePermission


class IsHRAdmin(BasePermission):
    message = "Only HR Administrators can perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == 'HRADMIN'


class CanManageLeave(BasePermission):
    message = "You do not have permission to approve/reject/cancel leave."

    def has_permission(self, request, view):
        user = request.user
        return user.profile.role == 'HRADMIN' or user.profile.can_manage_leave


class CanManageOvertime(BasePermission):
    message = "You do not have permission to approve/reject/cancel overtime."

    def has_permission(self, request, view):
        user = request.user
        return user.profile.role == 'HRADMIN' or user.profile.can_manage_overtime

class CanManageEmployees(BasePermission):
    message = "You do not have permission to manage employees."

    def has_permission(self, request, view):
        user = request.user
        return user.profile.role == 'HRADMIN' or user.profile.can_manage_employees


class CanDeleteRecords(BasePermission):
    message = "You do not have permission to delete records."

    def has_permission(self, request, view):
        user = request.user
        return user.profile.role == 'HRADMIN' or user.profile.can_delete_records


class CanLockPayroll(BasePermission):
    message = "You do not have permission to lock/unlock payroll."

    def has_permission(self, request, view):
        user = request.user
        return user.profile.role == 'HRADMIN' or user.profile.can_lock_payroll

class CanManageLeaveAdjustments(BasePermission):
    message = "You do not have permission to manage leave adjustments."

    def has_permission(self, request, view):
        user = request.user
        return (
            user.profile.role == 'HRADMIN'
            or user.profile.can_manage_leave_adjustments
        )      

class CanImportAttendance(BasePermission):
    message = "You do not have permission to import attendance."

    def has_permission(self, request, view):
        user = request.user
        return user.profile.role == 'HRADMIN' or user.profile.can_import_attendance 