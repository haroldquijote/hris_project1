import openpyxl
from datetime import date, datetime, time
from django.utils import timezone


def _parse_date(value):
    """Handle date or datetime objects returned by openpyxl."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Fallback for strings
    text = str(value).strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(record_date, value):
    """Combine a date with a time value into a timezone-aware datetime."""
    if value is None:
        return None

    time_part = None
    if isinstance(value, datetime):
        time_part = value.time()
    elif isinstance(value, time):
        time_part = value
    else:
        text = str(value).strip()
        for fmt in ('%H:%M:%S', '%H:%M', '%I:%M %p'):
            try:
                time_part = datetime.strptime(text, fmt).time()
                break
            except ValueError:
                continue

    if time_part is None:
        return None

    naive = datetime.combine(record_date, time_part)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def parse_xlsx(file):
    """Read the first sheet of an XLSX file and return a list of row dicts."""
    workbook = openpyxl.load_workbook(file, data_only=True)
    sheet = workbook.active

    # Build a case-insensitive map of header -> column index
    headers = [str(cell.value).strip().lower() if cell.value else ''
               for cell in sheet[1]]
    header_map = {name: idx for idx, name in enumerate(headers) if name}

    # Find the columns we need, allowing flexible naming
    emp_col = date_col = in_col = out_col = None
    for name, idx in header_map.items():
        if 'employee' in name and 'id' in name:
            emp_col = idx
        elif name == 'date':
            date_col = idx
        elif 'clock' in name and 'in' in name:
            in_col = idx
        elif 'clock' in name and 'out' in name:
            out_col = idx

    if emp_col is None or date_col is None:
        raise ValueError("Missing required columns: 'Employee ID' and 'Date'")

    rows = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        rows.append({
            'employee_id': row[emp_col],
            'date': row[date_col],
            'clock_in': row[in_col] if in_col is not None else None,
            'clock_out': row[out_col] if out_col is not None else None,
        })
    return rows

def _compute_status(employee, record_date, clock_in):
    """Return PRESENT, LATE, or ABSENT for a single day."""
    from attendance.models import AttendanceRecord

    if clock_in is None:
        return AttendanceRecord.Status.ABSENT

    schedule = employee.work_schedule
    if not schedule:
        return AttendanceRecord.Status.PRESENT

    # Is it a working day for this employee?
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
        # Working on a rest day – treat as present
        return AttendanceRecord.Status.PRESENT

    shift_start = schedule.shift_start
    grace = schedule.grace_period_minutes

    expected = datetime.combine(record_date, shift_start)
    expected = timezone.make_aware(expected, timezone.get_current_timezone())

    diff_minutes = (clock_in - expected).total_seconds() / 60
    
    if diff_minutes > grace:
       
        return AttendanceRecord.Status.LATE
    return AttendanceRecord.Status.PRESENT

def import_attendance(file):
    """Parse an XLSX file and create/update AttendanceRecords. Returns a summary."""
    from employees.models import Employee
    from attendance.models import AttendanceRecord

    rows = parse_xlsx(file)

    created = updated = errors = 0
    not_found_ids = set()
    error_details = []

    for row in rows:
        try:
            emp_id = str(row['employee_id']).strip() if row['employee_id'] else ''
            if not emp_id:
                continue

            try:
                employee = Employee.objects.get(company_id=emp_id)
            except Employee.DoesNotExist:
                not_found_ids.add(emp_id)
                continue

            record_date = _parse_date(row['date'])
            if record_date is None:
                errors += 1
                error_details.append(f"Invalid date for {emp_id}: {row['date']}")
                continue

            clock_in = _parse_time(record_date, row['clock_in'])
            clock_out = _parse_time(record_date, row['clock_out'])

            status = _compute_status(employee, record_date, clock_in)

            _, was_created = AttendanceRecord.objects.update_or_create(
                employee=employee,
                date=record_date,
                defaults={
                    'clock_in': clock_in,
                    'clock_out': clock_out,
                    'status': status,
                    'is_manual': False,
                }
            )

            if was_created:
                created += 1
            else:
                updated += 1

        except Exception as exc:
            errors += 1
            error_details.append(f"Row {row}: {exc}")

    return {
        'created': created,
        'updated': updated,
        'skipped_not_found': len(not_found_ids),
        'skipped_errors': errors,
        'not_found_ids': sorted(not_found_ids),
        'error_details': error_details,
    }