"""
DTR (Daily Time Record) builder.

Reads existing data, produces a per-day report for one employee for one pay period.

Design:
- 6 database queries total (employee, period, attendance, holidays, leaves, overtime)
- Pure Python computation after that — no N+1
- Every day in the period appears in the output, even rest days and absences
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from attendance.models import AttendanceRecord
from holidays.models import Holiday
from leave.models import LeaveRequest
from overtime.models import OvertimeRequest


# ============================================================================
# Public entry point
# ============================================================================

def build_dtr(employee, pay_period):
    """
    Build a full DTR for one employee over one pay period.

    Returns a dict with: employee, pay_period, rows, totals.
    """
    start = pay_period.start_date
    end = pay_period.end_date
    schedule = employee.work_schedule

    # ---- Bulk fetch everything (6 queries max) ----
    attendance_by_date = {
        a.date: a
        for a in AttendanceRecord.objects.filter(
            employee=employee, date__range=(start, end)
        )
    }

    holidays_by_date = {
        h.date: h
        for h in Holiday.objects.filter(date__range=(start, end))
    }

    leave_by_date = _build_leave_map(employee, start, end)
    overtime_by_date = _build_overtime_map(employee, start, end)

    # ---- Build one row per day ----
    rows = []
    current = start
    while current <= end:
        rows.append(_build_row(
            day=current,
            schedule=schedule,
            attendance=attendance_by_date.get(current),
            holiday=holidays_by_date.get(current),
            leave=leave_by_date.get(current),
            overtime_minutes=overtime_by_date.get(current, 0),
        ))
        current += timedelta(days=1)

    return {
        'employee': _serialize_employee(employee),
        'pay_period': _serialize_period(pay_period),
        'rows': rows,
        'totals': _compute_totals(rows),
    }


# ============================================================================
# Bulk loaders
# ============================================================================

def _build_leave_map(employee, start, end):
    """Return {date: LeaveRequest} expanding multi-day leaves."""
    leave_by_date = {}
    leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='APPROVED',
        start_date__lte=end,
        end_date__gte=start,
    ).select_related('leave_type')

    for leave in leaves:
        d = max(leave.start_date, start)
        d_end = min(leave.end_date, end)
        while d <= d_end:
            leave_by_date[d] = leave
            d += timedelta(days=1)

    return leave_by_date


def _build_overtime_map(employee, start, end):
    """Return {date: total_approved_overtime_minutes}."""
    overtime_by_date = {}
    for ot in OvertimeRequest.objects.filter(
        employee=employee,
        date__range=(start, end),
        status='APPROVED',
    ):
        minutes = int(ot.overtime_hours * 60)
        overtime_by_date[ot.date] = overtime_by_date.get(ot.date, 0) + minutes

    return overtime_by_date


# ============================================================================
# Single-row builder
# ============================================================================

def _build_row(day, schedule, attendance, holiday, leave, overtime_minutes):
    """
    Build a DTR row for one day.

    Status priority:
      1. Leave (if approved) → PAID_LEAVE / UNPAID_LEAVE / GOVERNMENT_LEAVE
      2. Attendance → PRESENT / LATE / INCOMPLETE
      3. Holiday → HOLIDAY
      4. Non-working day → REST_DAY
      5. Working day, no data → ABSENT
    """
    working_day = _is_working_day(schedule, day)

    row = {
        'date': day.isoformat(),
        'weekday': day.strftime('%A'),
        'clock_in': None,
        'clock_out': None,
        'hours_worked': None,
        'late_minutes': 0,
        'undertime_minutes': 0,
        'overtime_minutes': overtime_minutes,
        'status': 'ABSENT',
        'holiday_name': holiday.name if holiday else None,
        'holiday_type': holiday.holiday_type if holiday else None,
        'leave_type': None,
        'leave_paid': None,
        'remarks': attendance.remarks if attendance else '',
    }

    # ---- 1. Leave takes priority ----
    if leave:
        payment_status = leave.leave_type.payment_status
        row['status'] = f'{payment_status}_LEAVE'    # PAID_LEAVE / UNPAID_LEAVE / GOVERNMENT_LEAVE
        row['leave_type'] = leave.leave_type.name
        row['leave_paid'] = payment_status in ('PAID', 'GOVERNMENT')
        return row

    # ---- 2. Attendance ----
    if attendance and attendance.clock_in:
        local_in = timezone.localtime(attendance.clock_in)
        local_out = timezone.localtime(attendance.clock_out) if attendance.clock_out else None

        row['clock_in'] = local_in.strftime('%H:%M:%S')
        row['clock_out'] = local_out.strftime('%H:%M:%S') if local_out else None

        if local_out:
            delta = local_out - local_in
            row['hours_worked'] = round(delta.total_seconds() / 3600, 2)
        else:
            row['status'] = 'INCOMPLETE'
            return row

        # Late / undertime — only on working days with a schedule
        if working_day and schedule:
            shift_start = _aware_time(day, schedule.shift_start)
            shift_end = _aware_time(day, schedule.shift_end)
            grace = schedule.grace_period_minutes or 0

            late = (local_in - shift_start).total_seconds() / 60 - grace
            if late > 0:
                row['late_minutes'] = int(late)
                row['status'] = 'LATE'
            else:
                row['status'] = 'PRESENT'

            undertime = (shift_end - local_out).total_seconds() / 60
            if undertime > 0:
                row['undertime_minutes'] = int(undertime)
        else:
            # Worked on a rest day / holiday — counts as OT, not late
            row['status'] = 'PRESENT'

        return row

    # ---- 3. Holiday ----
    if holiday:
        row['status'] = 'HOLIDAY'
        return row

    # ---- 4. Rest day ----
    if not working_day:
        row['status'] = 'REST_DAY'
        return row

    # ---- 5. Absent ----
    row['status'] = 'ABSENT'
    return row


# ============================================================================
# Helpers
# ============================================================================

def _is_working_day(schedule, day):
    if not schedule:
        return True
    return {
        0: schedule.is_monday,
        1: schedule.is_tuesday,
        2: schedule.is_wednesday,
        3: schedule.is_thursday,
        4: schedule.is_friday,
        5: schedule.is_saturday,
        6: schedule.is_sunday,
    }.get(day.weekday(), False)


def _aware_time(day, t):
    """Combine a date + time and make it timezone-aware in the current tz."""
    naive = datetime.combine(day, t)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _serialize_employee(employee):
    return {
        'id': employee.id,
        'company_id': employee.company_id,
        'full_name': employee.full_name,
        'department': employee.department.name if employee.department else None,
        'job_title': employee.job_title.title if employee.job_title else None,
    }


def _serialize_period(pay_period):
    return {
        'id': pay_period.id,
        'start_date': pay_period.start_date.isoformat(),
        'end_date': pay_period.end_date.isoformat(),
        'label': (
            f"{pay_period.start_date.strftime('%b %d')} – "
            f"{pay_period.end_date.strftime('%b %d, %Y')}"
        ),
    }


def _compute_totals(rows):
    return {
        'total_days': len(rows),
        'days_present': sum(1 for r in rows if r['status'] in ('PRESENT', 'LATE', 'INCOMPLETE')),
        'days_late': sum(1 for r in rows if r['status'] == 'LATE'),
        'days_absent': sum(1 for r in rows if r['status'] == 'ABSENT'),
        'days_leave': sum(1 for r in rows if r['status'].endswith('_LEAVE')),
        'days_holiday': sum(1 for r in rows if r['status'] == 'HOLIDAY'),
        'days_rest': sum(1 for r in rows if r['status'] == 'REST_DAY'),
        'total_hours': round(sum(r['hours_worked'] or 0 for r in rows), 2),
        'total_late_minutes': sum(r['late_minutes'] for r in rows),
        'total_undertime_minutes': sum(r['undertime_minutes'] for r in rows),
        'total_overtime_minutes': sum(r['overtime_minutes'] for r in rows),
    }