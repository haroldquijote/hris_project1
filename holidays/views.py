from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Holiday
from .serializers import HolidaySerializer


class HolidayListCreateView(APIView):
    permission_classes = [IsAuthenticated]   

    def get(self, request):
        """List all holidays (optional year filter)"""
        year = request.query_params.get('year')
        queryset = Holiday.objects.all()
        if year:
            queryset = queryset.filter(date__year=year)
        serializer = HolidaySerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new holiday"""
        serializer = HolidaySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HolidayDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Holiday, pk=pk)

    def get(self, request, pk):
        holiday = self.get_object(pk)
        serializer = HolidaySerializer(holiday)
        return Response(serializer.data)

    def put(self, request, pk):
        holiday = self.get_object(pk)
        serializer = HolidaySerializer(holiday, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        holiday = self.get_object(pk)
        holiday.delete()
        return Response(
            {"message": "Holiday deleted"},
            status=status.HTTP_204_NO_CONTENT
        )


class HolidayCheckView(APIView):
    """Payroll (or any service) checks if a given date is a holiday"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response(
                {"error": "date query parameter is required (YYYY-MM-DD)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        holiday = Holiday.objects.filter(date=date_str).first()
        if not holiday:
            return Response(
                {"message": "Not a holiday"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = HolidaySerializer(holiday)
        return Response(serializer.data)