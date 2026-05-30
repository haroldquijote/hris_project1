from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import AttendanceRecord, WorkSchedule
from .serializers import AttendanceRecordSerializer, WorkScheduleSerializer


# ========== ATTENDANCE RECORD VIEWS ==========
class AttendanceListCreateView(APIView):
    permission_classes = [AllowAny]
    # ... (your existing code) ...

class AttendanceDetailView(APIView):
    permission_classes = [AllowAny]
    # ... (your existing code) ...


# ========== WORK SCHEDULE VIEWS ==========
class WorkScheduleListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        schedules = WorkSchedule.objects.all()
        serializer = WorkScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = WorkScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkScheduleDetailView(APIView):
    permission_classes = [AllowAny]

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
        # Optional: check if schedule has employees
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