from decimal import Decimal
from overtime.models import OvertimeRequest, OvertimeConfiguration
from attendance.models import WorkSchedule
from holidays.models import Holiday
from payroll.utils import get_annual_daily_rate


def determine_day_type(employee, date):
    """
    Determine the day type for overtime calculation.
    Returns one of: 'ORDINARY', 'REST_DAY', 'SPECIAL_NON_WORKING',
    'SPECIAL_ON_REST_DAY', 'REGULAR_HOLIDAY', 'REGULAR_ON_REST_DAY'.
    """
    # Check if holiday
    holiday = Holiday.objects.filter(date=date).first()
    schedule = employee.work_schedule

    # Is it a rest day? (not a working day according to schedule)
    if schedule:
        day_map = {
            0: schedule.is_monday,
            1: schedule.is_tuesday,
            2: schedule.is_wednesday,
            3: schedule.is_thursday,
            4: schedule.is_friday,
            5: schedule.is_saturday,
            6: schedule.is_sunday,
        }
        is_rest = not day_map.get(date.weekday(), False)
    else:
        # default: rest day if Saturday/Sunday
        is_rest = date.weekday() >= 5

    if holiday:
        if holiday.holiday_type == 'REGULAR':
            if is_rest:
                return 'REGULAR_ON_REST_DAY'
            return 'REGULAR_HOLIDAY'
        elif holiday.holiday_type == 'SPECIAL_NON_WORKING':
            if is_rest:
                return 'SPECIAL_ON_REST_DAY'
            return 'SPECIAL_NON_WORKING'
    else:
        if is_rest:
            return 'REST_DAY'
    return 'ORDINARY'


def compute_overtime_pay(employee, pay_period):
    """
    Return a dict with 'regular' and 'special' overtime pay totals for the employee.
    Regular = ordinary working day OT (multiplier 1.25)
    Special = rest day, special non‑working holiday, regular holiday OT (any multiplier > 1.25)
    Also includes a 'total' key that sums both.
    """
    from payroll.utils import get_annual_daily_rate

    approved_requests = OvertimeRequest.objects.filter(
        employee=employee,
        status=OvertimeRequest.Status.APPROVED,
        date__gte=pay_period.start_date,
        date__lte=pay_period.end_date,
    )

    if not approved_requests.exists():
        return {'regular': Decimal('0.00'), 'special': Decimal('0.00'), 'total': Decimal('0.00')}

    config = OvertimeConfiguration.load()
    year = pay_period.start_date.year
    daily_rate = get_annual_daily_rate(employee, year)
    if daily_rate is None or daily_rate == 0:
        return {'regular': Decimal('0.00'), 'special': Decimal('0.00'), 'total': Decimal('0.00')}

    hourly_rate = daily_rate / Decimal('8')
    regular_total = Decimal('0.00')
    special_total = Decimal('0.00')

    for ot_req in approved_requests:
        day_type = determine_day_type(employee, ot_req.date)

        # Map day type to multiplier
        multiplier_map = {
            'ORDINARY': config.ordinary_day_multiplier,
            'REST_DAY': config.rest_day_multiplier,
            'SPECIAL_NON_WORKING': config.special_non_working_holiday_multiplier,
            'SPECIAL_ON_REST_DAY': config.special_day_on_rest_day_multiplier,
            'REGULAR_HOLIDAY': config.regular_holiday_multiplier,
            'REGULAR_ON_REST_DAY': config.regular_holiday_on_rest_day_multiplier,
        }
        multiplier = Decimal(str(multiplier_map.get(day_type, config.ordinary_day_multiplier)))

        ot_hours = Decimal(ot_req.overtime_hours)
        pay = round(hourly_rate * multiplier * ot_hours, 2)

        if day_type == 'ORDINARY':
            regular_total += pay
        else:
            special_total += pay

    total = regular_total + special_total
    return {
        'regular': regular_total,
        'special': special_total,
        'total': total,
    }

def get_overtime_for_day(employee, day):
    """
    Return (hours, pay) for an employee on a given date if an approved overtime request exists.
    Otherwise return (0, 0).
    """
    ot_request = OvertimeRequest.objects.filter(
        employee=employee,
        date=day,
        status=OvertimeRequest.Status.APPROVED,
    ).first()

    if not ot_request:
        return Decimal('0.00'), Decimal('0.00')

    config = OvertimeConfiguration.load()
    year = day.year
    daily_rate = get_annual_daily_rate(employee, year)
    if daily_rate is None or daily_rate == 0:
        return Decimal('0.00'), Decimal('0.00')

    hourly_rate = daily_rate / Decimal('8')
    day_type = determine_day_type(employee, day)

    multiplier_map = {
        'ORDINARY': config.ordinary_day_multiplier,
        'REST_DAY': config.rest_day_multiplier,
        'SPECIAL_NON_WORKING': config.special_non_working_holiday_multiplier,
        'SPECIAL_ON_REST_DAY': config.special_day_on_rest_day_multiplier,
        'REGULAR_HOLIDAY': config.regular_holiday_multiplier,
        'REGULAR_ON_REST_DAY': config.regular_holiday_on_rest_day_multiplier,
    }
    multiplier = Decimal(str(multiplier_map.get(day_type, config.ordinary_day_multiplier)))

    hours = Decimal(ot_request.overtime_hours)
    pay = round(hourly_rate * multiplier * hours, 2)
    return hours, pay