from datetime import date
from django.db.models import Sum
from .models import LeaveGrant, LeaveRequest, LeaveAdjustment, LeaveConfiguration


def get_used_days(employee):
    """Total approved, non‑cancelled days for leave types that count."""
    approved_requests = LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveRequest.Status.APPROVED,
        leave_type__counts_towards_balance=True
    ).exclude(status=LeaveRequest.Status.CANCELLED)   # CANCELLED is separate status, but just in case

    total = 0
    for req in approved_requests:
        total += (req.end_date - req.start_date).days + 1
    return total


def get_balance(employee, as_of_date=None):
    if as_of_date is None:
        as_of_date = date.today()

    # Sum of non‑expired grants
    grants_sum = LeaveGrant.objects.filter(
        employee=employee,
        credited_on__lte=as_of_date,
        expires_on__gte=as_of_date
    ).aggregate(total=Sum('granted_days'))['total'] or 0

    used = get_used_days(employee)

    # Manual adjustments (sum of all)
    adjustments_sum = LeaveAdjustment.objects.filter(
        employee=employee
    ).aggregate(total=Sum('amount'))['total'] or 0

    return grants_sum - used + adjustments_sum


def get_current_annual_leave_days():
    config = LeaveConfiguration.load()
    return config.annual_leave_days