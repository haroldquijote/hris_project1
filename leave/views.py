from datetime import date, timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from employees.models import Employee
from payroll.models import PayPeriod

from .models import (
    LeaveType, LeaveGrant, LeaveRequest, LeaveAdjustment, LeaveConfiguration
)
from .serializers import (
    LeaveTypeSerializer, LeaveGrantSerializer, LeaveRequestSerializer,
    LeaveAdjustmentSerializer,
    LeaveRequestApproveSerializer, LeaveRequestRejectSerializer,
    LeaveRequestCancelSerializer
)
from .utils import get_balance, get_current_annual_leave_days


# ---------- Configuration ----------
class LeaveConfigurationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        config = LeaveConfiguration.load()
        return Response({'annual_leave_days': config.annual_leave_days})

    def put(self, request):
        config = LeaveConfiguration.load()
        days = request.data.get('annual_leave_days')
        if days is None:
            return Response({'error': 'annual_leave_days required'}, status=400)
        config.annual_leave_days = days
        config.save()
        return Response({'annual_leave_days': config.annual_leave_days})


# ---------- Leave Types ----------
class LeaveTypeListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        types = LeaveType.objects.all()
        serializer = LeaveTypeSerializer(types, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LeaveTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class LeaveTypeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(LeaveType, pk=pk)

    def get(self, request, pk):
        lt = self.get_object(pk)
        serializer = LeaveTypeSerializer(lt)
        return Response(serializer.data)

    def put(self, request, pk):
        lt = self.get_object(pk)
        serializer = LeaveTypeSerializer(lt, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        lt = self.get_object(pk)
        lt.delete()
        return Response(status=204)


# ---------- Leave Requests ----------
class LeaveRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = LeaveRequest.objects.all()
        employee = request.query_params.get('employee')
        status_q = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if employee:
            queryset = queryset.filter(employee_id=employee)
        if status_q:
            queryset = queryset.filter(status=status_q.upper())
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(end_date__lte=date_to)

        serializer = LeaveRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()   # status defaults to PENDING
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class LeaveRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(LeaveRequest, pk=pk)

    def get(self, request, pk):
        lr = self.get_object(pk)
        serializer = LeaveRequestSerializer(lr)
        return Response(serializer.data)

    def put(self, request, pk):
        """Full update of leave request fields (e.g., dates, reason)."""
        lr = self.get_object(pk)
        serializer = LeaveRequestSerializer(lr, data=request.data)
        if serializer.is_valid():
            # If the request is APPROVED and dates changed, we need to check balance for
            # the net change, to prevent negative balance.
            if lr.status == LeaveRequest.Status.APPROVED and \
               (serializer.validated_data.get('start_date') or serializer.validated_data.get('end_date')):
                old_days = lr.total_days()
                # Temporarily apply new dates to calculate new total
                # We'll use the validated data directly
                new_start = serializer.validated_data.get('start_date', lr.start_date)
                new_end = serializer.validated_data.get('end_date', lr.end_date)
                new_days = (new_end - new_start).days + 1
                net_change = new_days - old_days
                if net_change > 0 and lr.leave_type.counts_towards_balance:
                    balance = get_balance(lr.employee)
                    # Balance after applying net change: balance - net_change
                    if balance < net_change:
                        return Response(
                            {'error': f'Insufficient balance to increase leave days. {lr.employee.full_name} has {balance} day(s) remaining.'},
                            status=400
                        )
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        lr = self.get_object(pk)
        if lr.status not in [LeaveRequest.Status.PENDING]:
            return Response({'error': 'Only pending requests can be deleted.'}, status=400)
        lr.delete()
        return Response(status=204)


# ---------- Leave Actions (Approve / Reject / Cancel) ----------
class LeaveRequestApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        lr = get_object_or_404(LeaveRequest, pk=pk)

        # ===== LOCK CHECK START =====
        from payroll.models import PayPeriod
        from datetime import timedelta

        current = lr.start_date
        while current <= lr.end_date:
            if PayPeriod.objects.filter(
                start_date__lte=current,
                end_date__gte=current,
                status=PayPeriod.Status.LOCKED
            ).exists():
                return Response(
                    {'error': 'Cannot approve leave. Some days fall in a locked pay period.'},
                    status=400
                )
            current += timedelta(days=1)
        # ===== LOCK CHECK END =====

        serializer = LeaveRequestApproveSerializer(data=request.data, context={'request_obj': lr})
        if serializer.is_valid():
            lr.status = LeaveRequest.Status.APPROVED
            lr.reviewed_by = request.user
            lr.reviewed_at = timezone.now()
            lr.save()
            return Response(LeaveRequestSerializer(lr).data)
        return Response(serializer.errors, status=400)
    

class LeaveRequestRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        lr = get_object_or_404(LeaveRequest, pk=pk)
        serializer = LeaveRequestRejectSerializer(data=request.data, context={'request_obj': lr})
        if serializer.is_valid():
            lr.status = LeaveRequest.Status.REJECTED
            lr.reviewed_by = request.user
            lr.reviewed_at = timezone.now()
            lr.save()
            return Response(LeaveRequestSerializer(lr).data)
        return Response(serializer.errors, status=400)


class LeaveRequestCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        lr = get_object_or_404(LeaveRequest, pk=pk)
        serializer = LeaveRequestCancelSerializer(data=request.data, context={'request_obj': lr})
        if serializer.is_valid():
            lr.status = LeaveRequest.Status.CANCELLED
            lr.save()
            return Response(LeaveRequestSerializer(lr).data)
        return Response(serializer.errors, status=400)


# ---------- Balance & Reports ----------
class EmployeeBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get('employee')
        if not employee_id:
            return Response({'error': 'employee query param required'}, status=400)
        employee = get_object_or_404(Employee, pk=employee_id)
        balance = get_balance(employee)
        used = LeaveRequest.objects.filter(
            employee=employee,
            status=LeaveRequest.Status.APPROVED,
            leave_type__counts_towards_balance=True
        ).exclude(status=LeaveRequest.Status.CANCELLED)
        used_days = sum((r.end_date - r.start_date).days + 1 for r in used)

        grants = LeaveGrant.objects.filter(employee=employee)
        adjustments = LeaveAdjustment.objects.filter(employee=employee)

        return Response({
            'employee': employee.full_name,
            'balance': balance,
            'grants': LeaveGrantSerializer(grants, many=True).data,
            'used_days': used_days,
            'adjustments': LeaveAdjustmentSerializer(adjustments, many=True).data,
            'annual_leave_days': get_current_annual_leave_days(),
        })


class CurrentLeavesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        current = LeaveRequest.objects.filter(
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=today,
            end_date__gte=today
        )
        serializer = LeaveRequestSerializer(current, many=True)
        return Response(serializer.data)


class EmployeeLeaveHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        employee = get_object_or_404(Employee, pk=employee_id)
        leaves = LeaveRequest.objects.filter(employee=employee)
        serializer = LeaveRequestSerializer(leaves, many=True)
        return Response(serializer.data)


# ---------- Leave Adjustments ----------
class LeaveAdjustmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        adjustments = LeaveAdjustment.objects.all()
        serializer = LeaveAdjustmentSerializer(adjustments, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['created_by'] = request.user.id
        serializer = LeaveAdjustmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


# ---------- Annual Grant Generation ----------
class GenerateAnnualGrantsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Manual trigger: create grants for the previous calendar year.
        """
        from employees.models import Employee
        today = date.today()
        # Normally run on Jan 1 for the previous year
        year = today.year - 1   # Adjustable, but for simplicity we use previous year

        annual_days = get_current_annual_leave_days()
        employees = Employee.objects.filter(
            employment_status__in=['REGULAR', 'PROBATIONARY', 'CONTRACTUAL']
        )

        created = 0
        for emp in employees:
            # Determine months worked in the given 'year'
            # Employee must have been hired on or before Dec 31 of that year
            if emp.date_hired.year > year:
                continue  # hired after that year
            # Calculate months after hire month up to December of that year
            hire_year = emp.date_hired.year
            hire_month = emp.date_hired.month
            if hire_year < year:
                # full year
                months = 12
            else:
                # hired in the same year
                months = 12 - hire_month   # months after hire month
            if months <= 0:
                continue
            exact = (months / 12) * annual_days
            # standard rounding (round half up)
            granted = int(exact + 0.5)
            if granted <= 0:
                continue
            # Create grant for this employee
            credited = date(year + 1, 1, 1)
            expires = date(year + 2, 4, 30)
            LeaveGrant.objects.get_or_create(
                employee=emp,
                year=year,
                defaults={
                    'granted_days': granted,
                    'credited_on': credited,
                    'expires_on': expires,
                }
            )
            created += 1
        return Response({'message': f'Grants created for {created} employees.'})