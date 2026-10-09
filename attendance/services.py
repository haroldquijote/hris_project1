from datetime import datetime
from django.utils import timezone


def compute_attendance_status(employee, record_date, clock_in):
    """
    Determine attendance status from the employee's work schedule.

    Returns (status_code, note):
        status_code: 'PRESENT', 'LATE', 'REST_DAY', 'PAST_SHIFT'
        note: short explanation string, or None
    """
    schedule = employee.work_schedule
    if not schedule:
        return 'PRESENT', None

    day_map = {
        0: schedule.is_monday,
        1: schedule.is_tuesday,
        2: schedule.is_wednesday,
        3: schedule.is_thursday,
        4: schedule.is_friday,
        5: schedule.is_saturday,
        6: schedule.is_sunday,
    }

    if not day_map.get(record_date.weekday(), False):
        return 'REST_DAY', 'Not a working day'

    shift_start = schedule.shift_start
    shift_end = schedule.shift_end
    grace = schedule.grace_period_minutes or 0

    expected_start = timezone.make_aware(
        datetime.combine(record_date, shift_start),
        timezone.get_current_timezone(),
    )
    expected_end = timezone.make_aware(
        datetime.combine(record_date, shift_end),
        timezone.get_current_timezone(),
    )

    # Reject scans after shift end
    if clock_in > expected_end:
        return 'PAST_SHIFT', f'After shift end ({shift_end.strftime("%H:%M")})'

    diff_minutes = (clock_in - expected_start).total_seconds() / 60
    if diff_minutes > grace:
        return 'LATE', None

    return 'PRESENT', None