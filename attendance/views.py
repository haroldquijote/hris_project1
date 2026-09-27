from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from users.permissions import CanDeleteRecords
from rest_framework.permissions import IsAuthenticated
from .models import AttendanceRecord, WorkSchedule
from .serializers import AttendanceRecordSerializer, WorkScheduleSerializer
from audit.utils import log_action  
from rest_framework.parsers import MultiPartParser
from users.permissions import CanImportAttendance
from .utils.importer import import_attendance
import logging

logger = logging.getLogger(__name__)

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# ========== ATTENDANCE RECORD VIEWS ==========

class AttendanceListCreateView(APIView):
    permission_classes = [IsAuthenticated]  

    def get(self, request):
        """List all attendance records with optional filters"""
        records = AttendanceRecord.objects.all()

        employee_id = request.query_params.get('employee')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        status_filter = request.query_params.get('status')

        if employee_id:
            records = records.filter(employee_id=employee_id)
        if date_from:
            records = records.filter(date__gte=date_from)
        if date_to:
            records = records.filter(date__lte=date_to)
        if status_filter:
            records = records.filter(status=status_filter.upper())

        paginator = StandardPagination()
        paginated_records = paginator.paginate_queryset(records, request)
        serializer = AttendanceRecordSerializer(paginated_records, many=True)
        return paginator.get_paginated_response(serializer.data)
    
        

    def post(self, request):
        """Create a new attendance record (HR manual entry)"""
        serializer = AttendanceRecordSerializer(data=request.data)
        if serializer.is_valid():
            record = serializer.save()  
            log_action(request.user, 'CREATE', 'AttendanceRecord', record.id, f"Created attendance for {record.employee.full_name}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AttendanceDetailView(APIView):
    permission_classes = [IsAuthenticated]  

    def get_object(self, pk):
        return get_object_or_404(AttendanceRecord, pk=pk)

    def get(self, request, pk):
        record = self.get_object(pk)
        serializer = AttendanceRecordSerializer(record)
        return Response(serializer.data)

    def put(self, request, pk):
        record = self.get_object(pk)
        from payroll.models import PayPeriod
        if PayPeriod.objects.filter(
            start_date__lte=record.date,
            end_date__gte=record.date,
            status=PayPeriod.Status.LOCKED
        ).exists():
            return Response(
                {'error': 'Cannot edit attendance in a locked pay period.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = AttendanceRecordSerializer(record, data=request.data)
        if serializer.is_valid():
            serializer.save()
            log_action(request.user, 'UPDATE', 'AttendanceRecord', record.id, f"Updated attendance for {record.employee.full_name}")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self.permission_classes = [IsAuthenticated, CanDeleteRecords]
        self.check_permissions(request)
        record = self.get_object(pk)
        log_action(request.user, 'DELETE', 'AttendanceRecord', record.id, f"Deleted attendance for {record.employee.full_name}")
        record.delete()
        return Response(
            {"message": "Attendance record deleted"},
            status=status.HTTP_204_NO_CONTENT
        )


# ========== WORK SCHEDULE VIEWS ==========

class WorkScheduleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        schedules = WorkSchedule.objects.all()
        paginator = StandardPagination()
        paginated_schedules = paginator.paginate_queryset(schedules, request)
        serializer = WorkScheduleSerializer(paginated_schedules, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = WorkScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkScheduleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(WorkSchedule, pk=pk)

    def get(self, request, pk):
        schedule = self.get_object(pk)
        serializer = WorkScheduleSerializer(schedule)
        return Response(serializer.data)

    def put(self, request, pk):
        schedule = self.get_object(pk)
        serializer = WorkScheduleSerializer(schedule, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        schedule = self.get_object(pk)
        if schedule.employees.exists():
            return Response(
                {"error": "Cannot delete schedule assigned to employees."},
                status=status.HTTP_400_BAD_REQUEST
            )
        schedule.delete()
        return Response(
            {"message": "Work schedule deleted"},
            status=status.HTTP_204_NO_CONTENT
        )

class AttendanceImportView(APIView):
    permission_classes = [IsAuthenticated, CanImportAttendance]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No file provided. Use form field "file".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not file.name.lower().endswith('.xlsx'):
            return Response(
                {'error': 'Only .xlsx files are accepted.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            summary = import_attendance(file)
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            logger.exception("Attendance import failed")
            return Response(
                {'error': 'Import failed. Check the file format.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        log_action(
            request.user,
            'CREATE',
            'AttendanceImport',
            0,
            f"Imported attendance from {file.name}: "
            f"{summary['created']} created, {summary['updated']} updated, "
            f"{summary['skipped_not_found']} unknown IDs, "
            f"{summary['skipped_errors']} errors."
        )

        return Response(summary, status=status.HTTP_200_OK)