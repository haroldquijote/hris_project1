from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from users.permissions import IsHRAdmin
from employees.models import Employee
from .models import EmployeeLoan, LoanPayment
from .serializers import EmployeeLoanSerializer, LoanPaymentSerializer


class LoanListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def get(self, request):
        qs = EmployeeLoan.objects.select_related('employee').all()

        employee_id = request.query_params.get('employee')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        loan_type = request.query_params.get('loan_type')
        if loan_type:
            qs = qs.filter(loan_type=loan_type)

        return Response(EmployeeLoanSerializer(qs, many=True).data)

    def post(self, request):
        serializer = EmployeeLoanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        loan = serializer.save(created_by=request.user)
        return Response(
            EmployeeLoanSerializer(loan).data,
            status=status.HTTP_201_CREATED,
        )


class LoanDetailView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def get_object(self, pk):
        try:
            return EmployeeLoan.objects.select_related('employee').get(pk=pk)
        except EmployeeLoan.DoesNotExist:
            return None

    def get(self, request, pk):
        loan = self.get_object(pk)
        if not loan:
            return Response({'error': 'Loan not found'}, status=404)
        return Response(EmployeeLoanSerializer(loan).data)

    def patch(self, request, pk):
        loan = self.get_object(pk)
        if not loan:
            return Response({'error': 'Loan not found'}, status=404)

        # Prevent modifying if payments already exist
        if loan.payments.filter(reversed_at__isnull=True).exists():
            return Response(
                {'error': 'Cannot modify loan after payments have started. Cancel and create new.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EmployeeLoanSerializer(loan, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        loan = self.get_object(pk)
        if not loan:
            return Response({'error': 'Loan not found'}, status=404)

        loan.status = EmployeeLoan.Status.CANCELLED
        loan.save(update_fields=['status', 'updated_at'])
        return Response({'message': 'Loan cancelled', 'status': loan.status})


class LoanPaymentsView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def get(self, request, pk):
        try:
            loan = EmployeeLoan.objects.get(pk=pk)
        except EmployeeLoan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=404)

        payments = loan.payments.select_related('pay_period').all()
        return Response(LoanPaymentSerializer(payments, many=True).data)


class EmployeeLoanListView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def get(self, request, employee_id):
        try:
            employee = Employee.objects.get(pk=employee_id)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=404)

        qs = employee.loans.select_related('employee').all()
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return Response(EmployeeLoanSerializer(qs, many=True).data)


class LoanPaymentReverseView(APIView):
    """
    Reverse a single loan payment.
    Use this to fix a mistake — deletes the payment, restores balance.
    """
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def post(self, request, loan_id, payment_id):
        try:
            loan = EmployeeLoan.objects.get(pk=loan_id)
        except EmployeeLoan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=404)

        try:
            payment = loan.payments.get(pk=payment_id)
        except LoanPayment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=404)

        if payment.reversed_at:
            return Response(
                {'error': 'Payment already reversed'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            loan.balance += payment.amount
            loan.periods_paid = max(0, loan.periods_paid - 1)
            if loan.status == EmployeeLoan.Status.COMPLETED:
                loan.status = EmployeeLoan.Status.ACTIVE
            loan.save()

            payment.reversed_at = timezone.now()
            payment.reversed_by = request.user
            payment.save()

        return Response({
            'message': 'Payment reversed',
            'loan': EmployeeLoanSerializer(loan).data,
        })