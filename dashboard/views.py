from datetime import date, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Avg, Q
from employees.models import Employee
from attendance.models import AttendanceRecord
from leave.models import LeaveRequest
from payroll.models import PayPeriod, Payslip
from recruitment.models import JobPosting, Candidate
from holidays.models import Holiday


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ---------- date handling ----------
        start_str = request.query_params.get('start_date')
        end_str = request.query_params.get('end_date')
        if start_str and end_str:
            range_start = date.fromisoformat(start_str)
            range_end = date.fromisoformat(end_str)
        else:
            # default: today for attendance/leave, latest pay period for payroll
            range_start = range_end = date.today()

        # ---------- 1. Employee Headcount ----------
        active_employees = Employee.objects.exclude(
            employment_status__in=['RESIGNED', 'TERMINATED']
        )
        headcount_total = active_employees.count()
        headcount_by_status = (
            active_employees.values('employment_status')
            .annotate(count=Count('id'))
            .order_by('employment_status')
        )
        headcount = {
            'total_active': headcount_total,
            'by_status': {item['employment_status']: item['count'] for item in headcount_by_status}
        }

        # ---------- 2. Attendance Overview ----------
        attendance_filter = Q(date__gte=range_start, date__lte=range_end)
        if start_str and end_str:
            attendance_filter = Q(date__gte=range_start, date__lte=range_end)
        else:
            attendance_filter = Q(date=date.today())

        attendance_records = AttendanceRecord.objects.filter(attendance_filter)
        present = attendance_records.filter(status='PRESENT').count()
        late = attendance_records.filter(status='LATE').count()
        absent = attendance_records.filter(status='ABSENT').count()
        # on leave today (approved leave that covers today)
        on_leave_today = LeaveRequest.objects.filter(
            status='APPROVED',
            start_date__lte=range_end,
            end_date__gte=range_start
        ).count()

        attendance_overview = {
            'date': str(range_start),
            'present': present,
            'late': late,
            'absent': absent,
            'on_leave': on_leave_today
        }

        # ---------- 3. Leave Summary ----------
        pending_approvals = LeaveRequest.objects.filter(status='PENDING').count()
        currently_on_leave = LeaveRequest.objects.filter(
            status='APPROVED',
            start_date__lte=date.today(),
            end_date__gte=date.today()
        )
        currently_on_leave_names = [f"{req.employee.first_name} {req.employee.last_name}" for req in currently_on_leave]

        leave_summary = {
            'pending_approvals': pending_approvals,
            'currently_on_leave': currently_on_leave_names
        }

        # ---------- 4. Payroll Totals ----------
        # latest locked period, or if date range provided, sum overlapping periods
        if start_str and end_str:
            # find periods that overlap the range
            periods = PayPeriod.objects.filter(
                start_date__lte=range_end,
                end_date__gte=range_start,
                status=PayPeriod.Status.LOCKED
            )
            payslips = Payslip.objects.filter(pay_period__in=periods)
            employee_count = payslips.values('employee').distinct().count()
            totals = payslips.aggregate(
                total_gross=Sum('gross_pay'),
                total_net=Sum('net_pay'),
                total_deductions=(
                    Sum('sss_deduction') + Sum('philhealth_deduction') +
                    Sum('pagibig_deduction') + Sum('tax_deduction') +
                    Sum('late_deduction_total') + Sum('absent_deduction_total') +
                    Sum('undertime_deduction_total')
                ),
            )
            payroll_totals = {
                'period': 'custom_range',
                'total_gross_pay': totals['total_gross'] or 0,
                'total_net_pay': totals['total_net'] or 0,
                'total_deductions': totals['total_deductions'] or 0,
                'employee_count': employee_count,
            }
        else:
            latest_period = PayPeriod.objects.filter(
                status=PayPeriod.Status.LOCKED
            ).order_by('-start_date').first()
            if latest_period:
                payslips = Payslip.objects.filter(pay_period=latest_period)
                employee_count = payslips.values('employee').distinct().count()
                totals = payslips.aggregate(
                    total_gross=Sum('gross_pay'),
                    total_net=Sum('net_pay'),
                    total_deductions=(
                        Sum('sss_deduction') + Sum('philhealth_deduction') +
                        Sum('pagibig_deduction') + Sum('tax_deduction') +
                        Sum('late_deduction_total') + Sum('absent_deduction_total') +
                        Sum('undertime_deduction_total')
                    ),
                )
                payroll_totals = {
                    'period': {
                        'start_date': str(latest_period.start_date),
                        'end_date': str(latest_period.end_date),
                        'status': latest_period.status
                    },
                    'total_gross_pay': totals['total_gross'] or 0,
                    'total_net_pay': totals['total_net'] or 0,
                    'total_deductions': totals['total_deductions'] or 0,
                    'employee_count': employee_count,
                }
            else:
                payroll_totals = {
                    'period': None,
                    'total_gross_pay': 0,
                    'total_net_pay': 0,
                    'total_deductions': 0,
                    'employee_count': 0,
                }

        # ---------- 5. Recruitment Pipeline ----------
        open_jobs = JobPosting.objects.count()
        active_candidates = Candidate.objects.filter(status__in=['APPLIED', 'SHORTLISTED'])
        total_candidates = active_candidates.count()
        avg_score = active_candidates.exclude(llm_score=0).aggregate(avg=Avg('llm_score'))['avg'] or 0

        recruitment = {
            'open_jobs': open_jobs,
            'total_candidates': total_candidates,
            'average_score': round(float(avg_score), 1)
        }

        # ---------- 6. Holidays ----------
        today = date.today()

        # Holidays today
        today_holidays = [
            {
                'name': h.name,
                'date': str(h.date),
                'holiday_type': h.holiday_type,
                'percentage': str(h.percentage),
            }
            for h in Holiday.objects.filter(date=today).order_by('name')
        ]

        # Upcoming holidays (strictly after today, within 30 days)
        upcoming_holidays = [
            {
                'name': h.name,
                'date': str(h.date),
                'holiday_type': h.holiday_type,
                'percentage': str(h.percentage),
            }
            for h in Holiday.objects.filter(
                date__gt=today,
                date__lte=today + timedelta(days=30)
            ).order_by('date')
        ]

        total_holidays_this_month = Holiday.objects.filter(
            date__year=today.year, date__month=today.month
        ).count()

        total_holidays_this_year = Holiday.objects.filter(
            date__year=today.year
        ).count()

        holidays = {
            'today': today_holidays,
            'upcoming': upcoming_holidays,
            'total_this_month': total_holidays_this_month,
            'total_this_year': total_holidays_this_year,
        }
        return Response({
            'employee_headcount': headcount,
            'attendance_overview': attendance_overview,
            'leave_summary': leave_summary,
            'payroll_totals': payroll_totals,
            'recruitment_pipeline': recruitment,
            'holidays': holidays, 
        })