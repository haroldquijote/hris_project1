from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.permissions import CanManageOvertime, IsHRAdmin
from audit.utils import log_action
from .models import OvertimeRequest, OvertimeConfiguration
from .serializers import OvertimeRequestSerializer, OvertimeConfigurationSerializer
from payroll.models import PayPeriod  


class OvertimeRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = OvertimeRequest.objects.all()
        employee = request.query_params.get('employee')
        status_q = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if employee:
            queryset = queryset.filter(employee_id=employee)
        if status_q:
            queryset = queryset.filter(status=status_q.upper())
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        serializer = OvertimeRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OvertimeRequestSerializer(data=request.data)
        if serializer.is_valid():
            ot = serializer.save()   
            log_action(request.user, 'CREATE', 'OvertimeRequest', ot.id, f"Created overtime for {ot.employee.full_name}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OvertimeRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(OvertimeRequest, pk=pk)

    def get(self, request, pk):
        ot = self.get_object(pk)
        serializer = OvertimeRequestSerializer(ot)
        return Response(serializer.data)

    def put(self, request, pk):
        ot = self.get_object(pk)
        if ot.status != OvertimeRequest.Status.PENDING:
            return Response({'error': 'Only pending requests can be edited.'}, status=400)
        serializer = OvertimeRequestSerializer(ot, data=request.data)
        if serializer.is_valid():
            serializer.save()
            log_action(request.user, 'UPDATE', 'OvertimeRequest', ot.id, f"Updated overtime request for {ot.employee.full_name}")
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class OvertimeRequestApproveView(APIView):
    permission_classes = [IsAuthenticated, CanManageOvertime]

    def post(self, request, pk):
        ot = get_object_or_404(OvertimeRequest, pk=pk)
        if ot.status != OvertimeRequest.Status.PENDING:
            return Response({'error': 'Only pending requests can be approved.'}, status=400)

        # Check if the pay period containing this date is locked
        period = PayPeriod.objects.filter(
            start_date__lte=ot.date, end_date__gte=ot.date
        ).first()
        if period and period.status == PayPeriod.Status.LOCKED:
            return Response({'error': 'Cannot approve overtime. The pay period is locked.'}, status=400)

        ot.status = OvertimeRequest.Status.APPROVED
        ot.approved_by = request.user
        ot.approved_at = timezone.now()
        ot.save()
        log_action(request.user, 'APPROVE', 'OvertimeRequest', ot.id, f"Approved overtime for {ot.employee.full_name}")
        serializer = OvertimeRequestSerializer(ot)
        return Response(serializer.data)


class OvertimeRequestCancelView(APIView):
    permission_classes = [IsAuthenticated, CanManageOvertime]

    def post(self, request, pk):
        ot = get_object_or_404(OvertimeRequest, pk=pk)
        if ot.status != OvertimeRequest.Status.APPROVED:
            return Response({'error': 'Only approved requests can be cancelled.'}, status=400)
        ot.status = OvertimeRequest.Status.CANCELLED
        ot.approved_by = request.user
        ot.approved_at = timezone.now()
        ot.save()
        log_action(request.user, 'CANCEL', 'OvertimeRequest', ot.id, f"Cancelled overtime for {ot.employee.full_name}")
        serializer = OvertimeRequestSerializer(ot)
        return Response(serializer.data)

class OvertimeRequestRejectView(APIView):
    permission_classes = [IsAuthenticated, CanManageOvertime]

    def post(self, request, pk):
        ot = get_object_or_404(OvertimeRequest, pk=pk)
        if ot.status != OvertimeRequest.Status.PENDING:
            return Response({'error': 'Only pending requests can be rejected.'}, status=400)
        ot.status = OvertimeRequest.Status.REJECTED
        ot.approved_by = request.user
        ot.approved_at = timezone.now()
        ot.save()
        log_action(request.user, 'REJECT', 'OvertimeRequest', ot.id, f"Rejected overtime for {ot.employee.full_name}")
        serializer = OvertimeRequestSerializer(ot)
        return Response(serializer.data)


class OvertimeConfigurationView(APIView):
    permission_classes = [IsAuthenticated]   
    def get(self, request):
        config = OvertimeConfiguration.load()
        serializer = OvertimeConfigurationSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        # Only HRAdmin can update overtime multipliers
        self.permission_classes = [IsAuthenticated, IsHRAdmin]
        self.check_permissions(request)

        config = OvertimeConfiguration.load()
        serializer = OvertimeConfigurationSerializer(config, data=request.data)
        if serializer.is_valid():
            serializer.save()
            log_action(request.user, 'UPDATE', 'OvertimeConfiguration', config.pk, "Updated overtime multipliers")
            return Response(serializer.data)
        return Response(serializer.errors, status=400)