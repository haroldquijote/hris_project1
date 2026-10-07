from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.utils import timezone
import csv
from django.http import HttpResponse
from audit.utils import log_action
from .models import PayPeriod, Payslip, PayslipDailyDetail, PayslipAdjustment, CompanySettings, SSSContribution, PhilHealthContribution, PagIBIGContribution, WithholdingTaxTable
from .serializers import PayPeriodSerializer, PayslipSerializer, PayslipDailyDetailSerializer, PayslipAdjustmentSerializer
from .utils import compute_phase2_gross_pay
from employees.models import Employee, EmployeeSalary
from .gov_deductions import compute_government_deductions
from overtime.overtime_utils import compute_overtime_pay, get_overtime_for_day, determine_day_type
from leave.utils import get_balance
from users.permissions import CanLockPayroll
from .utils import compute_net_pay
import base64

# ---------- Pay Period CRUD ----------
class PayPeriodListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        periods = PayPeriod.objects.all()
        serializer = PayPeriodSerializer(periods, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PayPeriodSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PayPeriodDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(PayPeriod, pk=pk)

    def get(self, request, pk):
        period = self.get_object(pk)
        serializer = PayPeriodSerializer(period)
        return Response(serializer.data)

    def put(self, request, pk):
        period = self.get_object(pk)
        serializer = PayPeriodSerializer(period, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- Compute Gross Pay ----------
class ComputeGrossPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        pay_period = get_object_or_404(PayPeriod, pk=pk)

        # ---------- Block if period is locked ----------
        if pay_period.status == PayPeriod.Status.LOCKED:
            return Response(
                {'error': 'Cannot recompute payslips for a locked period.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        active_employees = Employee.objects.exclude(
            employment_status__in=['RESIGNED', 'TERMINATED']
        )
         # -----------------------------------------------
        created_count = 0
        skipped_count = 0

        for employee in active_employees:
            result = compute_phase2_gross_pay(employee, pay_period)
            if result is None:
                skipped_count += 1
                continue

            # ───────────── 1. Compute overtime (once) ─────────────
            overtime_data = compute_overtime_pay(employee, pay_period)
            overtime_regular_pay = overtime_data['regular']
            overtime_special_pay = overtime_data['special']
            overtime_total = overtime_data['total']

            # ───────────── 2. Gross pay including overtime ─────────
            gross_pay = result['gross_pay'] + overtime_total

            # ───────────── 3. Government deductions (based on new gross) ─────────
                        # ───────────── 3. Government deductions (based on new gross) ─────────
            if gross_pay == 0:
                # If the employee earned nothing this period, no government
                # contributions or withholding tax are withheld. The employer
                # will handle deferred contributions manually.
                gov_deductions = {
                    'sss': Decimal('0'),
                    'philhealth': Decimal('0'),
                    'pagibig': Decimal('0'),
                    'tax': Decimal('0'),
                }
            elif pay_period.period_type == PayPeriod.PeriodType.REGULAR:
                gov_deductions = compute_government_deductions(
                    employee, pay_period, gross_pay
                )
            else:   # THIRTEENTH_MONTH or any other special type
                gov_deductions = {
                    'sss': Decimal('0'),
                    'philhealth': Decimal('0'),
                    'pagibig': Decimal('0'),
                    'tax': Decimal('0'),
                }
            
             # ───────────── Count absences and leaves from daily details ─────────────
            absence_count = 0
            leave_count = 0
            absence_dates_list = []
            leave_dates_list = []

            for detail in result['daily_details']:
                if detail['status'] == 'ABSENT':
                    if detail.get('leave_type_name'):
                        # This is a leave day – count only as leave, not absence
                        leave_count += 1
                        leave_dates_list.append(str(detail['date']))
                    else:
                        # Genuine absence – no leave label
                        absence_count += 1
                        absence_dates_list.append(str(detail['date']))
                # Undertime/Late days are not counted here because the payslip sample
                # only shows "No. of Absence" and "No. of Leave". (Lates/Undertime are
                # shown as monetary deductions only.)
            # ───────────── Remaining leave balance ─────────────
            
            remaining = get_balance(employee, as_of_date=pay_period.end_date)

            # ───────────── 4. Create/update the Payslip ─────────────
            payslip, _ = Payslip.objects.update_or_create(
                employee=employee,
                pay_period=pay_period,
                defaults={
                    'basic_pay': result['basic_pay'],
                    'allowances_total': result['allowances_total'],
                    'late_deduction_total': result['late_deduction_total'],
                    'absent_deduction_total': result['absent_deduction_total'],
                    'undertime_deduction_total': result['undertime_deduction_total'],
                    'holiday_pay_total': result['holiday_pay_total'],
                    'rest_day_premium_total': result['rest_day_premium_total'],
                    'overtime_pay': overtime_total,
                    'overtime_regular_pay': overtime_regular_pay,
                    'overtime_special_pay': overtime_special_pay,
                    'nsd_total': result['nsd_total'],
                    'gross_pay': gross_pay,
                    'sss_deduction': gov_deductions['sss'],
                    'philhealth_deduction': gov_deductions['philhealth'],
                    'pagibig_deduction': gov_deductions['pagibig'],
                    'tax_deduction': gov_deductions['tax'],
                    'absence_count': absence_count,
                    'absence_dates': absence_dates_list,
                    'leave_count': leave_count,
                    'leave_dates': leave_dates_list,
                    'remaining_leave_balance': remaining,
                    'status': Payslip.Status.DRAFT,
                }
            )

            # ───────────── 5. Recalculate net pay with adjustments ─────────
            payslip.net_pay = compute_net_pay(payslip)
            payslip.save()

            # ───────────── 6. Enrich daily details with overtime info ─────────────
            # This loop adds overtime minutes, pay, and type to each day before saving
            for detail in result['daily_details']:
                if detail['working_day']:
                        ot_hours, ot_pay = get_overtime_for_day(employee, detail['date'])
                        if ot_hours > 0:
                            detail['overtime_minutes'] = int(ot_hours * 60)
                            detail['overtime_pay'] = ot_pay
                            detail['overtime_type'] = determine_day_type(employee, detail['date'])
                        else:
                            detail['overtime_minutes'] = 0
                            detail['overtime_pay'] = Decimal('0.00')
                            detail['overtime_type'] = None
                else:
                        detail['overtime_minutes'] = 0
                        detail['overtime_pay'] = Decimal('0.00')
                        detail['overtime_type'] = None

            # ───────────── 7. Recreate daily details (with overtime fields) ─────────
            payslip.daily_details.all().delete()
            daily_objects = []
            for detail in result['daily_details']:
                daily_objects.append(PayslipDailyDetail(
                    payslip=payslip,
                    date=detail['date'],
                    working_day=detail['working_day'],
                    status=detail['status'],
                    night_shift_diff=detail.get('night_shift_diff', Decimal('0.00')),
                    late_minutes=detail['late_minutes'],
                    late_deduction=detail.get('late_deduction', Decimal('0.00')), 
                    undertime_minutes=detail.get('undertime_minutes', 0),
                    undertime_deduction=detail.get('undertime_deduction', Decimal('0.00')),
                    absent_deduction=detail['absent_deduction'],
                    holiday_extra=detail['holiday_extra'],
                    holiday=detail.get('holiday'),
                    holiday_type=detail.get('holiday_type'),
                    leave_type_name=detail.get('leave_type_name'),
                    overtime_minutes=detail.get('overtime_minutes', 0),
                    overtime_pay=detail.get('overtime_pay', Decimal('0.00')),
                    overtime_type=detail.get('overtime_type'),
                    remarks=detail['remarks'],
                ))
            PayslipDailyDetail.objects.bulk_create(daily_objects)

            created_count += 1
            log_action(request.user, 'UPDATE', 'Payslip', payslip.id, f"Computed payslip for {payslip.employee.full_name}")
        return Response({
            'message': f'Payslips generated for {created_count} employees. '
                       f'{skipped_count} skipped (no active salary).'
        }, status=status.HTTP_200_OK)


# ---------- Payslip List / Detail ----------
class PayslipListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get('pay_period')
        if period_id:
            payslips = Payslip.objects.select_related('pay_period').filter(pay_period_id=period_id)
        else:
            payslips = Payslip.objects.select_related('pay_period').all()
        serializer = PayslipSerializer(payslips, many=True)
        return Response(serializer.data)
    
class PayslipDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, pk):
        return get_object_or_404(Payslip, pk=pk)
    def get(self, request, pk):
        payslip = self.get_object(pk)
        serializer = PayslipSerializer(payslip)
        return Response(serializer.data)

class PayslipDailyDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, payslip_id):
        payslip = get_object_or_404(Payslip, pk=payslip_id)
        details = payslip.daily_details.all().order_by('date')
        serializer = PayslipDailyDetailSerializer(details, many=True)
        return Response(serializer.data)

class PayslipAdjustmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payslip_id):
        payslip = get_object_or_404(Payslip, pk=payslip_id)
        adjustments = payslip.adjustments.all()
        serializer = PayslipAdjustmentSerializer(adjustments, many=True)
        return Response(serializer.data)

    def post(self, request, payslip_id):
        payslip = get_object_or_404(Payslip, pk=payslip_id)
        data = request.data.copy()
        data['payslip'] = payslip.id
        serializer = PayslipAdjustmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            # Recalculate net pay for the payslip
            payslip.refresh_from_db()
            payslip.net_pay = compute_net_pay(payslip)
            payslip.save()
            return Response(PayslipSerializer(payslip).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CompanySettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings = CompanySettings.load()
        logo = None
        if settings.logo_data and settings.logo_content_type:
            logo = f"data:{settings.logo_content_type};base64,{settings.logo_data}"
        return Response({
            'company_name': settings.company_name,
            'logo': logo,
        })

    def put(self, request):
        settings = CompanySettings.load()
        settings.company_name = request.data.get('company_name', settings.company_name)
        if 'logo' in request.FILES:
            logo_file = request.FILES['logo']
            settings.logo_data = base64.b64encode(logo_file.read()).decode('utf-8')
            settings.logo_content_type = logo_file.content_type
        settings.save()
        return Response({'message': 'Company settings updated'})

class PayPeriodLockView(APIView):
    permission_classes = [IsAuthenticated, CanLockPayroll]


    def post(self, request, pk):
        pay_period = get_object_or_404(PayPeriod, pk=pk)

        if pay_period.status == PayPeriod.Status.LOCKED:
            return Response({'error': 'Period is already locked.'}, status=status.HTTP_400_BAD_REQUEST)

        pay_period.status = PayPeriod.Status.LOCKED
        pay_period.locked_by = request.user
        pay_period.locked_at = timezone.now()
        pay_period.save()
        log_action(request.user, 'LOCK', 'PayPeriod', pay_period.id, f"Locked pay period {pay_period.start_date} to {pay_period.end_date}")

        # Optionally mark all DRAFT payslips as FINAL
        finalize = request.data.get('finalize_payslips', True)
        if finalize:
            Payslip.objects.filter(
                pay_period=pay_period,
                status=Payslip.Status.DRAFT
            ).update(status=Payslip.Status.FINAL, updated_at=timezone.now())

        return Response({'message': 'Period locked successfully.'}, status=status.HTTP_200_OK)


class PayPeriodUnlockView(APIView):
    permission_classes = [IsAuthenticated, CanLockPayroll]


    def post(self, request, pk):
        pay_period = get_object_or_404(PayPeriod, pk=pk)

        if pay_period.status != PayPeriod.Status.LOCKED:
            return Response({'error': 'Period is not locked.'}, status=status.HTTP_400_BAD_REQUEST)

        pay_period.status = PayPeriod.Status.OPEN
        pay_period.unlocked_by = request.user
        pay_period.unlocked_at = timezone.now()
        pay_period.save()
        log_action(request.user, 'UNLOCK', 'PayPeriod', pay_period.id, f"Unlocked pay period {pay_period.start_date} to {pay_period.end_date}")

        return Response({'message': 'Period unlocked successfully.'}, status=status.HTTP_200_OK)


class PayrollRegisterCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get('pay_period')
        if not period_id:
            return Response(
                {'error': 'pay_period query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pay_period = get_object_or_404(PayPeriod, pk=period_id)
        payslips = Payslip.objects.filter(pay_period=pay_period)\
            .select_related('employee__job_title', 'employee__department')\
            .prefetch_related('daily_details', 'adjustments')

        response = HttpResponse(content_type='text/csv')
        filename = f"payroll_register_{pay_period.start_date}_{pay_period.end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # ---------- HEADER (no iPad column, adjustments combined) ----------
        writer.writerow([
            'Employee Name',
            'Position',
            'Monthly Rate',
            'Semi-Monthly',
            'Daily Rate',
            'Hourly Rate',
            'Basic Rate',
            # OT Regular
            'OT Reg (mins)', 'OT Reg (pay)',
            # OT Special
            'OT Spec (mins)', 'OT Spec (pay)',
            # Rest Day
            'RD Hrs', 'RD Prem',
            # Legal Holiday
            'Leg Hol (days)', 'Leg Hol (pay)',
            # Special Holiday
            'Spcl Hol (days)', 'Spcl Hol (pay)',
            # NSD
            'NSD Hrs', 'NSD (pay)',
            'Allowance',
            'Gross Pay',
            # Deductions
            'SSS', 'Pag-IBIG', 'PhilHealth',
            'Loans/Adj',          # <-- all adjustments here (iPad, loans, etc.)
            'Absent (days)', 'Absent (deduction)',
            'Late (mins)', 'Late (deduction)',
            'Undertime (mins)', 'Undertime (deduction)',
            'Total Deductions',
            'Net Pay',
        ])

        # ---------- TOTALS ACCUMULATORS ----------
        totals = {col: Decimal('0.00') for col in [
            'monthly_rate', 'semi_monthly', 'daily_rate', 'hourly_rate',
            'basic_rate',
            'ot_reg_mins', 'ot_reg_pay',
            'ot_spec_mins', 'ot_spec_pay',
            'rd_hours', 'rd_prem',
            'leg_hol_days', 'leg_hol_pay',
            'spcl_hol_days', 'spcl_hol_pay',
            'nsd_hours', 'nsd_pay',
            'allowance', 'gross_pay',
            'sss', 'pagibig', 'philhealth', 'loans',
            'absent_days', 'absent_deduction',
            'late_mins', 'late_deduction',
            'undertime_mins', 'undertime_deduction',
            'total_deductions', 'net_pay',
        ]}

        # ---------- PROCESS EACH PAYSLIP ----------
        for payslip in payslips:
            employee = payslip.employee
            details = payslip.daily_details.all()
            adjustments = payslip.adjustments.all()

            # --- Salary information ---
            active_salary = EmployeeSalary.objects.filter(
                employee=employee, end_date__isnull=True
            ).first()
            monthly_rate = active_salary.base_salary if active_salary else Decimal('0.00')
            semi_monthly_full = monthly_rate / 2

            # Annual daily rate (standard formula: monthly * 12 / 261)
            daily_rate = round((monthly_rate * 12) / Decimal('365'), 2) if monthly_rate > 0 else Decimal('0.00')
            hourly_rate = round(daily_rate / Decimal('8'), 2) if daily_rate > 0 else Decimal('0.00')

            position = employee.job_title.title if employee.job_title else ''

            # --- OT Regular (ordinary days) ---
            ot_reg_mins = sum(d.overtime_minutes for d in details if d.overtime_type == 'ORDINARY')
            ot_reg_pay = sum(d.overtime_pay for d in details if d.overtime_type == 'ORDINARY')

            # --- OT Special (rest days, holidays, etc.) ---
            ot_spec_mins = sum(d.overtime_minutes for d in details if d.overtime_type and d.overtime_type != 'ORDINARY')
            ot_spec_pay = sum(d.overtime_pay for d in details if d.overtime_type and d.overtime_type != 'ORDINARY')

            # --- Rest Day ---
            rd_days = sum(1 for d in details if d.rest_day_premium > 0)
            rd_hours = rd_days * 8
            rd_prem = payslip.rest_day_premium_total

            # --- Legal Holiday ---
            leg_hol_details = [d for d in details if d.holiday_type == 'REGULAR']
            leg_hol_days = len(leg_hol_details)
            leg_hol_pay = sum(d.holiday_extra for d in leg_hol_details)

            # --- Special Holiday ---
            spcl_hol_details = [d for d in details if d.holiday_type == 'SPECIAL_NON_WORKING']
            spcl_hol_days = len(spcl_hol_details)
            spcl_hol_pay = sum(d.holiday_extra for d in spcl_hol_details)

            # --- NSD (hours and pay) ---
            nsd_pay_total = payslip.nsd_total
            nsd_hours = Decimal('0')
            if nsd_pay_total > 0 and hourly_rate > 0:
                nsd_hours = round(nsd_pay_total / (hourly_rate * Decimal('0.10')), 2)

            # --- Allowances ---
            allowance = payslip.allowances_total

            # --- Gross Pay ---
            gross_pay = payslip.gross_pay

            # --- Deductions ---
            sss = payslip.sss_deduction
            pagibig = payslip.pagibig_deduction
            philhealth = payslip.philhealth_deduction

            # All adjustments combined (loans, iPad, etc.)
            total_loans = sum(adj.amount for adj in adjustments)

            absent_days = payslip.absence_count
            absent_deduction = payslip.absent_deduction_total

            total_late_mins = sum(d.late_minutes for d in details)
            late_deduction = payslip.late_deduction_total

            undertime_mins = sum(d.undertime_minutes for d in details)
            undertime_deduction = payslip.undertime_deduction_total

            # Total deductions (SSS, Pag‑IBIG, PhilHealth, loans, absences, lates, undertime)
            total_deductions = (
                sss + pagibig + philhealth + total_loans +
                absent_deduction + late_deduction + undertime_deduction
            )

            # Net pay
            net_pay = payslip.net_pay

            # Write the row
            writer.writerow([
                employee.full_name,
                position,
                monthly_rate,
                semi_monthly_full,
                daily_rate,
                hourly_rate,
                monthly_rate,   # Basic Rate (same as monthly)
                ot_reg_mins, ot_reg_pay,
                ot_spec_mins, ot_spec_pay,
                rd_hours, rd_prem,
                leg_hol_days, leg_hol_pay,
                spcl_hol_days, spcl_hol_pay,
                nsd_hours, nsd_pay_total,
                allowance,
                gross_pay,
                sss, pagibig, philhealth,
                total_loans,          # <-- single column for all adjustments
                absent_days, absent_deduction,
                total_late_mins, late_deduction,
                undertime_mins, undertime_deduction,
                total_deductions,
                net_pay,
            ])

            # Update totals
            totals['monthly_rate'] += monthly_rate
            totals['semi_monthly'] += semi_monthly_full
            totals['daily_rate'] += daily_rate
            totals['hourly_rate'] += hourly_rate
            totals['basic_rate'] += monthly_rate
            totals['ot_reg_mins'] += ot_reg_mins
            totals['ot_reg_pay'] += ot_reg_pay
            totals['ot_spec_mins'] += ot_spec_mins
            totals['ot_spec_pay'] += ot_spec_pay
            totals['rd_hours'] += rd_hours
            totals['rd_prem'] += rd_prem
            totals['leg_hol_days'] += leg_hol_days
            totals['leg_hol_pay'] += leg_hol_pay
            totals['spcl_hol_days'] += spcl_hol_days
            totals['spcl_hol_pay'] += spcl_hol_pay
            totals['nsd_hours'] += nsd_hours
            totals['nsd_pay'] += nsd_pay_total
            totals['allowance'] += allowance
            totals['gross_pay'] += gross_pay
            totals['sss'] += sss
            totals['pagibig'] += pagibig
            totals['philhealth'] += philhealth
            totals['loans'] += total_loans
            totals['absent_days'] += absent_days
            totals['absent_deduction'] += absent_deduction
            totals['late_mins'] += total_late_mins
            totals['late_deduction'] += late_deduction
            totals['undertime_mins'] += undertime_mins
            totals['undertime_deduction'] += undertime_deduction
            totals['total_deductions'] += total_deductions
            totals['net_pay'] += net_pay

        # ---------- TOTALS ROW ----------
        writer.writerow([])  # empty separator row
        writer.writerow([
            'TOTALS',
            '',  # position
            totals['monthly_rate'],
            totals['semi_monthly'],
            totals['daily_rate'],
            totals['hourly_rate'],
            totals['basic_rate'],
            totals['ot_reg_mins'], totals['ot_reg_pay'],
            totals['ot_spec_mins'], totals['ot_spec_pay'],
            totals['rd_hours'], totals['rd_prem'],
            totals['leg_hol_days'], totals['leg_hol_pay'],
            totals['spcl_hol_days'], totals['spcl_hol_pay'],
            totals['nsd_hours'], totals['nsd_pay'],
            totals['allowance'],
            totals['gross_pay'],
            totals['sss'], totals['pagibig'], totals['philhealth'],
            totals['loans'],
            totals['absent_days'], totals['absent_deduction'],
            totals['late_mins'], totals['late_deduction'],
            totals['undertime_mins'], totals['undertime_deduction'],
            totals['total_deductions'],
            totals['net_pay'],
        ])

        return response

class SSSRemittanceCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get('pay_period')
        if not period_id:
            return Response({'error': 'pay_period query parameter is required.'}, status=400)

        pay_period = get_object_or_404(PayPeriod, pk=period_id)
        if pay_period.status != PayPeriod.Status.LOCKED:
            return Response({'error': 'The pay period must be locked before downloading remittance reports.'}, status=400)

        payslips = Payslip.objects.filter(pay_period=pay_period).select_related('employee')

        response = HttpResponse(content_type='text/csv')
        filename = f"SSS_Remittance_{pay_period.start_date}_{pay_period.end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Employee Name', 'SSS Number', 'Monthly Salary Credit', 'Employee Share', 'Employer Share', 'Total'])

        totals = {'employee_share': Decimal('0.00'), 'employer_share': Decimal('0.00'), 'total': Decimal('0.00')}

        for payslip in payslips:
            employee = payslip.employee
            active_salary = EmployeeSalary.objects.filter(employee=employee, end_date__isnull=True).first()
            if not active_salary:
                continue
            monthly_salary = active_salary.base_salary

            # Get MSC and employee share from the SSS contribution table (same lookup as in gov_deductions)
            sss_row = SSSContribution.objects.filter(
                salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
            ).first()
            if not sss_row:
                continue

            msc = sss_row.monthly_salary_credit
            employee_share = sss_row.employee_share   # 5% of MSC already computed
            employer_share = msc * Decimal('0.10')    # 10% of MSC
            total = employee_share + employer_share

            writer.writerow([
                employee.full_name,
                employee.sss_gsis_no or '',
                msc,
                employee_share,
                employer_share,
                total,
            ])

            totals['employee_share'] += employee_share
            totals['employer_share'] += employer_share
            totals['total'] += total

        writer.writerow([])
        writer.writerow(['TOTALS', '', '', totals['employee_share'], totals['employer_share'], totals['total']])
        return response


class PhilHealthRemittanceCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get('pay_period')
        if not period_id:
            return Response({'error': 'pay_period query parameter is required.'}, status=400)

        pay_period = get_object_or_404(PayPeriod, pk=period_id)
        if pay_period.status != PayPeriod.Status.LOCKED:
            return Response({'error': 'The pay period must be locked before downloading remittance reports.'}, status=400)

        payslips = Payslip.objects.filter(pay_period=pay_period).select_related('employee')

        response = HttpResponse(content_type='text/csv')
        filename = f"PhilHealth_Remittance_{pay_period.start_date}_{pay_period.end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Employee Name', 'PhilHealth Number', 'Monthly Basic Salary', 'Employee Share', 'Employer Share', 'Total'])

        totals = {'employee_share': Decimal('0.00'), 'employer_share': Decimal('0.00'), 'total': Decimal('0.00')}

        for payslip in payslips:
            employee = payslip.employee
            active_salary = EmployeeSalary.objects.filter(employee=employee, end_date__isnull=True).first()
            if not active_salary:
                continue
            monthly_salary = active_salary.base_salary

            # Look up PhilHealth rate from the contribution table
            phil_row = PhilHealthContribution.objects.filter(
                salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
            ).first()
            if not phil_row:
                continue

            # Apply floor and ceiling (10,000 – 100,000)
            salary_for_phil = min(max(monthly_salary, Decimal('10000')), Decimal('100000'))
            employee_share = round(salary_for_phil * phil_row.employee_share_rate, 2)
            employer_share = round(salary_for_phil * (phil_row.premium_rate - phil_row.employee_share_rate), 2)
            total = employee_share + employer_share

            writer.writerow([
                employee.full_name,
                employee.philhealth or '',
                monthly_salary,
                employee_share,
                employer_share,
                total,
            ])

            totals['employee_share'] += employee_share
            totals['employer_share'] += employer_share
            totals['total'] += total

        writer.writerow([])
        writer.writerow(['TOTALS', '', '', totals['employee_share'], totals['employer_share'], totals['total']])
        return response

class PagIBIGRemittanceCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get('pay_period')
        if not period_id:
            return Response({'error': 'pay_period query parameter is required.'}, status=400)

        pay_period = get_object_or_404(PayPeriod, pk=period_id)
        if pay_period.status != PayPeriod.Status.LOCKED:
            return Response({'error': 'The pay period must be locked before downloading remittance reports.'}, status=400)

        payslips = Payslip.objects.filter(pay_period=pay_period).select_related('employee')

        response = HttpResponse(content_type='text/csv')
        filename = f"PagIBIG_Remittance_{pay_period.start_date}_{pay_period.end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Employee Name', 'Pag-IBIG Number', 'Monthly Basic Salary', 'Employee Share', 'Employer Share', 'Total'])

        totals = {'employee_share': Decimal('0.00'), 'employer_share': Decimal('0.00'), 'total': Decimal('0.00')}

        for payslip in payslips:
            employee = payslip.employee
            active_salary = EmployeeSalary.objects.filter(employee=employee, end_date__isnull=True).first()
            if not active_salary:
                continue
            monthly_salary = active_salary.base_salary

            # Look up Pag-IBIG contribution
            pagibig_row = PagIBIGContribution.objects.filter(
                salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
            ).first()
            if not pagibig_row:
                continue

            # Employee share: computed similarly as in gov_deductions
            base_for_pagibig = min(monthly_salary, Decimal('10000'))
            if pagibig_row.employee_share < Decimal('1'):  # rate
                if pagibig_row.employee_share == Decimal('0.01'):
                    employee_share = min(base_for_pagibig * Decimal('0.01'), Decimal('200'))
                else:
                    employee_share = min(base_for_pagibig * Decimal('0.02'), Decimal('200'))
            else:
                employee_share = pagibig_row.employee_share

            # Employer share: 2% of salary, capped at 200
            employer_share = min(base_for_pagibig * Decimal('0.02'), Decimal('200'))

            total = employee_share + employer_share

            writer.writerow([
                employee.full_name,
                employee.hdmf or '',
                monthly_salary,
                employee_share,
                employer_share,
                total,
            ])

            totals['employee_share'] += employee_share
            totals['employer_share'] += employer_share
            totals['total'] += total

        writer.writerow([])
        writer.writerow(['TOTALS', '', '', totals['employee_share'], totals['employer_share'], totals['total']])
        return response


class BIRRemittanceCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get('pay_period')
        if not period_id:
            return Response({'error': 'pay_period query parameter is required.'}, status=400)

        pay_period = get_object_or_404(PayPeriod, pk=period_id)
        if pay_period.status != PayPeriod.Status.LOCKED:
            return Response({'error': 'The pay period must be locked before downloading remittance reports.'}, status=400)

        # Get all employees who have a payslip in this period
        payslips = Payslip.objects.filter(pay_period=pay_period).select_related('employee')

        response = HttpResponse(content_type='text/csv')
        filename = f"BIR_Remittance_{pay_period.start_date}_{pay_period.end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Employee Name', 'TIN', 'Gross Compensation', 'Taxable Income', 'Tax Withheld'])

        totals = {'gross': Decimal('0.00'), 'taxable': Decimal('0.00'), 'tax': Decimal('0.00')}


        for payslip in payslips:
            employee = payslip.employee
            active_salary = EmployeeSalary.objects.filter(employee=employee, end_date__isnull=True).first()
            if not active_salary:
                continue
            monthly_salary = active_salary.base_salary

            # Monthly gross compensation (approximate by doubling semi‑monthly gross)
            monthly_gross = payslip.gross_pay * 2

            # Monthly employee contributions (from contribution tables, same as gov_deductions)
            sss_row = SSSContribution.objects.filter(
                salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
            ).first()
            sss_monthly = sss_row.employee_share if sss_row else Decimal('0.00')

            phil_row = PhilHealthContribution.objects.filter(
                salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
            ).first()
            if phil_row:
                salary_for_phil = min(max(monthly_salary, Decimal('10000')), Decimal('100000'))
                phil_monthly = round(salary_for_phil * phil_row.employee_share_rate, 2)
            else:
                phil_monthly = Decimal('0.00')

            pagibig_row = PagIBIGContribution.objects.filter(
                salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
            ).first()
            if pagibig_row:
                base_for_pagibig = min(monthly_salary, Decimal('10000'))
                if pagibig_row.employee_share < Decimal('1'):
                    if pagibig_row.employee_share == Decimal('0.01'):
                        pagibig_monthly = min(base_for_pagibig * Decimal('0.01'), Decimal('200'))
                    else:
                        pagibig_monthly = min(base_for_pagibig * Decimal('0.02'), Decimal('200'))
                else:
                    pagibig_monthly = pagibig_row.employee_share
            else:
                pagibig_monthly = Decimal('0.00')

            # Taxable income = gross - SSS - PhilHealth - Pag‑IBIG
            taxable_income = monthly_gross - sss_monthly - phil_monthly - pagibig_monthly
            if taxable_income < 0:
                taxable_income = Decimal('0.00')

            # Compute monthly withholding tax
            tax_monthly = Decimal('0.00')
            tax_row = WithholdingTaxTable.objects.filter(
            tax_status=employee.tax_status,
            compensation_from__lte=taxable_income,
            compensation_to__gte=taxable_income,
            ).first()

            if tax_row:
                tax_monthly = tax_row.base_tax + (taxable_income - tax_row.compensation_from) * tax_row.rate_above
                if tax_monthly < 0:
                    tax_monthly = Decimal('0.00')

            writer.writerow([
                employee.full_name,
                employee.tin or '',
                f"{monthly_gross:.2f}",
                f"{taxable_income:.2f}",
                f"{tax_monthly:.2f}",
            ])

            totals['gross'] += monthly_gross
            totals['taxable'] += taxable_income
            totals['tax'] += tax_monthly

        writer.writerow([])
        writer.writerow(['TOTALS', '', totals['gross'], totals['taxable'], totals['tax']])
        return response