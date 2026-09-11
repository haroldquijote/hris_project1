import calendar
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.utils import timezone
from employees.models import Employee, EmployeeSalary, EmployeeAllowance
from attendance.models import AttendanceRecord
from holidays.models import Holiday
from leave.models import LeaveRequest
from overtime.models import OvertimeConfiguration


# ----------------------------------------------------------------------
# Working day helpers (unchanged)
# ----------------------------------------------------------------------
def is_working_day(day, schedule):
    if not schedule:
        return day.weekday() < 5
    day_map = {
        0: schedule.is_monday,
        1: schedule.is_tuesday,
        2: schedule.is_wednesday,
        3: schedule.is_thursday,
        4: schedule.is_friday,
        5: schedule.is_saturday,
        6: schedule.is_sunday,
    }
    return day_map.get(day.weekday(), False)


def count_working_days_in_year(year, schedule):
    """Return total working days in a full calendar year according to the schedule."""
    count = 0
    for month in range(1, 13):
        num_days = calendar.monthrange(year, month)[1]
        for day in range(1, num_days + 1):
            if is_working_day(date(year, month, day), schedule):
                count += 1
    return count


def count_weekdays_in_year(year):
    """Return total Monday‑Friday days in a calendar year."""
    count = 0
    for month in range(1, 13):
        num_days = calendar.monthrange(year, month)[1]
        for day in range(1, num_days + 1):
            if date(year, month, day).weekday() < 5:
                count += 1
    return count

def determine_day_type(employee, date):
    """
    Determine the day type for an employee on a given date.
    Returns one of:
    'ORDINARY', 'REST_DAY', 'SPECIAL_NON_WORKING',
    'SPECIAL_ON_REST_DAY', 'REGULAR_HOLIDAY', 'REGULAR_ON_REST_DAY'
    """
    from holidays.models import Holiday
    from attendance.models import WorkSchedule

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
        is_rest = date.weekday() >= 5   # Saturday or Sunday

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


# ----------------------------------------------------------------------
# Annual daily rate (monthly-paid, divisor = working days in the year)
# ----------------------------------------------------------------------
def get_annual_daily_rate(employee, year):
    active_salary = EmployeeSalary.objects.filter(employee=employee, end_date__isnull=True).first()
    if not active_salary:
        return None
    # Use 365‑day factor (standard Philippine formula for monthly‑paid)
    return (Decimal(active_salary.base_salary) * 12) / Decimal('365')

# ----------------------------------------------------------------------
# Main Phase 2 computation (per‑minute deduction)
# ----------------------------------------------------------------------
def compute_phase2_gross_pay(employee, pay_period):
    active_salary = EmployeeSalary.objects.filter(employee=employee, end_date__isnull=True).first()
    # Load first‑8‑hour multipliers from database (singleton)
    config = OvertimeConfiguration.load()
    first8_multipliers = {
        'ORDINARY': Decimal('1.00'),   # always 1.00 for ordinary day
        'REST_DAY': config.rest_day_first8_multiplier,
        'SPECIAL_NON_WORKING': config.special_non_working_first8_multiplier,
        'SPECIAL_ON_REST_DAY': config.special_on_rest_day_first8_multiplier,
        'REGULAR_HOLIDAY': config.regular_holiday_first8_multiplier,
        'REGULAR_ON_REST_DAY': config.regular_on_rest_day_first8_multiplier,
    }
    if not active_salary:
        return None

    # Active allowances
    active_allowances = EmployeeAllowance.objects.filter(employee=employee, end_date__isnull=True)
    total_monthly_allowance = sum(a.amount for a in active_allowances)

    month = pay_period.start_date.month
    year = pay_period.start_date.year
    days_in_month = calendar.monthrange(year, month)[1]
    days_in_period = (pay_period.end_date - pay_period.start_date).days + 1

    # Prorated allowances for the period
    allowances_total = round((total_monthly_allowance / days_in_month) * days_in_period, 2)

    # Annual daily rate (fixed for the whole year)
    daily_rate = get_annual_daily_rate(employee, year)
    if daily_rate is None or daily_rate == 0:
        return None

    schedule = employee.work_schedule
    # Shift times and grace period – always provided even if schedule is None
    if schedule:
        shift_start = schedule.shift_start
        shift_end = schedule.shift_end
        grace_minutes = schedule.grace_period_minutes
    else:
        shift_start = datetime.strptime('09:00', '%H:%M').time()
        shift_end = datetime.strptime('18:00', '%H:%M').time()
        grace_minutes = 0   # strict no‑grace when no schedule

    shift_hours = 8
    current_tz = timezone.get_current_timezone()

    # Accumulators
    late_deduction_total = Decimal('0.00')
    absent_deduction_total = Decimal('0.00')
    undertime_deduction_total = Decimal('0.00')
    rest_day_premium_total = Decimal('0.00')
    holiday_pay_total = Decimal('0.00')
    nsd_total = Decimal('0.00')
    daily_details = []

    current_day = pay_period.start_date
    while current_day <= pay_period.end_date:
        working_day = is_working_day(current_day, schedule)
        detail = {
            'date': current_day,
            'working_day': working_day,
            'status': 'REST_DAY' if not working_day else '',
            'absent_deduction': Decimal('0.00'),
            'late_minutes': 0,
            'late_deduction': Decimal('0.00'),
            'undertime_minutes': 0,
            'undertime_deduction': Decimal('0.00'),
            'night_shift_diff': Decimal('0.00'),
            'rest_day_premium': Decimal('0.00'),
            'holiday': None,    
            'holiday_extra': Decimal('0.00'),
            'remarks': '',
        }


        attendance = AttendanceRecord.objects.filter(employee=employee, date=current_day).first()
        holiday = Holiday.objects.filter(date=current_day).first()

# ---------- Approved (unpaid) leave ----------
        approved_leave = LeaveRequest.objects.filter(
            employee=employee,
            status='APPROVED',
            start_date__lte=current_day,
            end_date__gte=current_day
        ).select_related('leave_type').first()

        if approved_leave:
            deduction = round(daily_rate, 2)
            detail['status'] = 'ABSENT'
            detail['absent_deduction'] = deduction
            detail['leave_type_name'] = approved_leave.leave_type.name
            detail['remarks'] = f'On leave: {approved_leave.leave_type.name}'
            absent_deduction_total += deduction
            daily_details.append(detail)
            current_day += timedelta(days=1)
            continue

        
        # ---------- Absent ----------
        if not attendance or attendance.status == 'ABSENT':
            # If it's a rest day and no attendance record, it's a normal rest day
            if not working_day and not attendance:
                detail['status'] = 'REST_DAY'
                daily_details.append(detail)
                current_day += timedelta(days=1)
                continue
            # Otherwise, it's a genuine absence
            deduction = round(daily_rate, 2)
            detail['status'] = 'ABSENT'
            detail['absent_deduction'] = deduction
            absent_deduction_total += deduction
            daily_details.append(detail)
            current_day += timedelta(days=1)
            continue

        # ---------- Time‑based late / undertime ----------
        late_minutes = 0
        undertime_minutes = 0
        late_deduction = Decimal('0.00')       
        undertime_deduction = Decimal('0.00')   

        if attendance.clock_in:
            clock_in_dt = attendance.clock_in.astimezone(current_tz)
            shift_start_aware = timezone.make_aware(datetime.combine(current_day, shift_start), current_tz)
            diff = (clock_in_dt - shift_start_aware).total_seconds() / 60
            if diff > grace_minutes:
                late_minutes = int(diff - grace_minutes)

        if attendance.clock_out:
            clock_out_dt = attendance.clock_out.astimezone(current_tz)
            shift_end_aware = timezone.make_aware(datetime.combine(current_day, shift_end), current_tz)
            diff = (shift_end_aware - clock_out_dt).total_seconds() / 60
            if diff > 0:
                undertime_minutes = int(diff)

        per_minute_rate = daily_rate / (shift_hours * 60)
        late_deduction = round(late_minutes * per_minute_rate, 2)
        undertime_deduction = round(undertime_minutes * per_minute_rate, 2)

        detail['late_minutes'] = late_minutes
        detail['late_deduction'] = late_deduction
        detail['undertime_minutes'] = undertime_minutes
        detail['undertime_deduction'] = undertime_deduction

        # Accumulate late/undertime totals
        if working_day:
            late_deduction_total += late_deduction
            undertime_deduction_total += undertime_deduction


         # ---- Night Shift Differential (NSD) ----
        nsd_pay = Decimal('0.00')
        if attendance.clock_in and attendance.clock_out:
            hourly_rate = daily_rate / Decimal(shift_hours)
            # NSD window: 10 PM (current_day) to 6 AM (next day)
            nsd_start = timezone.make_aware(
                datetime.combine(current_day, datetime.strptime('22:00', '%H:%M').time()),
                current_tz
            )
            nsd_end = timezone.make_aware(
                datetime.combine(current_day + timedelta(days=1), datetime.strptime('06:00', '%H:%M').time()),
                current_tz
            )
            clock_in_dt = attendance.clock_in.astimezone(current_tz)
            clock_out_dt = attendance.clock_out.astimezone(current_tz)

            overlap_start = max(clock_in_dt, nsd_start)
            overlap_end = min(clock_out_dt, nsd_end)
            if overlap_start < overlap_end:
                overlap_seconds = (overlap_end - overlap_start).total_seconds()
                nsd_hours = overlap_seconds / 3600
                nsd_pay = round(Decimal(str(nsd_hours)) * hourly_rate * Decimal('0.10'), 2)

        detail['night_shift_diff'] = nsd_pay
        nsd_total += nsd_pay

        # ---- Determine day type and rest day premium ----
        day_type = determine_day_type(employee, current_day)
        total_first8_mult = first8_multipliers.get(day_type, Decimal('1.00'))
        holiday_mult = Decimal(holiday.percentage) / 100 if holiday else Decimal('1.00')
        rest_day_premium_amount = round(daily_rate * (total_first8_mult - holiday_mult), 2)

        # For rest days, ignore late/undertime
        if not working_day:
            detail['late_minutes'] = 0
            detail['late_deduction'] = Decimal('0.00')
            detail['undertime_minutes'] = 0
            detail['undertime_deduction'] = Decimal('0.00')

        if rest_day_premium_amount > 0:
            detail['rest_day_premium'] = rest_day_premium_amount
            rest_day_premium_total += rest_day_premium_amount

        # Determine attendance status (based on minutes)
        if late_minutes > 0 and undertime_minutes > 0:
            detail['status'] = 'LATE_UNDERTIME'
        elif late_minutes > 0:
            detail['status'] = 'LATE'
        elif undertime_minutes > 0:
            detail['status'] = 'UNDERTIME'
        else:
            detail['status'] = 'PRESENT'

        # Holiday premium (if worked)
        if holiday:
            percentage = Decimal(str(holiday.percentage))
            premium = round(daily_rate * (percentage - 100) / 100, 2)
            detail['holiday_extra'] = premium
            detail['holiday'] = holiday.name
            detail['holiday_type'] = holiday.holiday_type
            detail['remarks'] = f'Holiday: {holiday.name}'
            holiday_pay_total += premium
        else:
            detail['holiday'] = None
            detail['holiday_type'] = None
            detail['holiday_extra'] = Decimal('0.00')

        daily_details.append(detail)
        current_day += timedelta(days=1)

    
    # Basic pay = fixed half-monthly amount for standard semi-monthly periods
    monthly_salary = Decimal(active_salary.base_salary)

    # Detect whether this is a standard semi-monthly period
    is_first_half = (
        pay_period.start_date.day == 1
        and pay_period.end_date.day == 15
    )
    is_second_half = (
        pay_period.start_date.day == 16
        and pay_period.end_date.day == days_in_month
    )

    if is_first_half or is_second_half:
        # Monthly-paid employee: fixed half of monthly salary per payday
        prorated_basic = round(monthly_salary / Decimal('2'), 2)
    else:
        # Non-standard period (e.g., a 1-day test period) → fall back to day proration
        prorated_basic = round(
            (monthly_salary / Decimal(days_in_month)) * Decimal(days_in_period), 2
        )


    total_deductions = late_deduction_total + absent_deduction_total + undertime_deduction_total
    basic_pay = round(prorated_basic - total_deductions, 2)
    if basic_pay < 0:
        basic_pay = Decimal('0.00')

    # ---------------------------------------------------------------
    # Edge case: full-period absence.
    # If every working day in the period was absent (no attendance, no
    # approved leave), the employee should earn ₱0 for the period. This
    # prevents a small residual amount from appearing when the fixed
    # half-monthly pay is slightly higher than the sum of daily-rate
    # deductions.
    # ---------------------------------------------------------------
    working_days_in_period = sum(1 for d in daily_details if d['working_day'])
    absent_days_in_period = sum(
        1 for d in daily_details
        if d['working_day'] and d['status'] == 'ABSENT'
    )
    if working_days_in_period > 0 and absent_days_in_period == working_days_in_period:
        basic_pay = Decimal('0.00')

    gross_pay = round(basic_pay + Decimal(allowances_total) + holiday_pay_total +
                      rest_day_premium_total + nsd_total, 2)

    return {
        'basic_pay': basic_pay,
        'allowances_total': allowances_total,
        'late_deduction_total': late_deduction_total,
        'absent_deduction_total': absent_deduction_total,
        'undertime_deduction_total': undertime_deduction_total,
        'holiday_pay_total': holiday_pay_total,
        'rest_day_premium_total': rest_day_premium_total,
        'nsd_total': nsd_total,
        'gross_pay': gross_pay,
        'daily_details': daily_details,
    }

def compute_net_pay(payslip):
    """
    Compute net pay with the negative clamp.
    Used by both ComputeGrossPayView and PayslipAdjustmentListCreateView.
    """
    gov_total = (
        payslip.sss_deduction
        + payslip.philhealth_deduction
        + payslip.pagibig_deduction
        + payslip.tax_deduction
    )
    adj_total = sum(adj.amount for adj in payslip.adjustments.all())
    net = payslip.gross_pay - gov_total + adj_total
    return max(net, Decimal('0.00'))