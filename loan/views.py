import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from users.permissions import CanManageLoans, IsHRAdmin
from employees.models import Employee
from .models import EmployeeLoan, LoanPayment
from .serializers import EmployeeLoanSerializer, LoanPaymentSerializer
from audit.utils import log_action


logger = logging.getLogger(__name__)


class LoanListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageLoans]

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
            logger.warning(
                f"Loan creation failed — user={request.user.username} "
                f"payload={request.data} errors={serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        loan = serializer.save(created_by=request.user)

        log_action(
            request.user, 'CREATE', 'EmployeeLoan', loan.id,
            f"Created {loan.display_name} for {loan.employee.full_name} — "
            f"₱{loan.principal_amount} / {loan.months_to_pay}mo"
        )
        logger.info(
            f"Loan #{loan.id} created — {loan.employee.company_id} "
            f"{loan.display_name} ₱{loan.principal_amount} "
            f"({loan.months_to_pay}mo) by {request.user.username}"
        )

        return Response(
            EmployeeLoanSerializer(loan).data,
            status=status.HTTP_201_CREATED,
        )


class LoanDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageLoans]

    def get_object(self, pk):
        try:
            return EmployeeLoan.objects.select_related('employee').get(pk=pk)
        except EmployeeLoan.DoesNotExist:
            return None

    def get(self, request, pk):
        loan = self.get_object(pk)
        if not loan:
            logger.warning(f"Loan #{pk} not found — user={request.user.username}")
            return Response({'error': 'Loan not found'}, status=404)
        return Response(EmployeeLoanSerializer(loan).data)

    def patch(self, request, pk):
        loan = self.get_object(pk)
        if not loan:
            logger.warning(f"Loan #{pk} not found for PATCH — user={request.user.username}")
            return Response({'error': 'Loan not found'}, status=404)

        if loan.payments.filter(reversed_at__isnull=True).exists():
            logger.warning(
                f"Loan #{pk} modification blocked — payments exist "
                f"— user={request.user.username}"
            )
            return Response(
                {'error': 'Cannot modify loan after payments have started. Cancel and create new.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EmployeeLoanSerializer(loan, data=request.data, partial=True)
        if not serializer.is_valid():
            logger.warning(
                f"Loan #{pk} PATCH failed — user={request.user.username} "
                f"errors={serializer.errors}"
            )
            return Response(serializer.errors, status=400)
        serializer.save()

        log_action(
            request.user, 'UPDATE', 'EmployeeLoan', loan.id,
            f"Modified {loan.display_name} for {loan.employee.full_name}"
        )
        logger.info(f"Loan #{loan.id} updated by {request.user.username}")

        return Response(serializer.data)

    def delete(self, request, pk):
        loan = self.get_object(pk)
        if not loan:
            logger.warning(f"Loan #{pk} not found for DELETE — user={request.user.username}")
            return Response({'error': 'Loan not found'}, status=404)

        old_status = loan.status
        balance_at_cancel = loan.balance

        loan.status = EmployeeLoan.Status.CANCELLED
        loan.save(update_fields=['status', 'updated_at'])

        log_action(
            request.user, 'DELETE', 'EmployeeLoan', loan.id,
            f"Cancelled {loan.display_name} for {loan.employee.full_name} — "
            f"balance was ₱{balance_at_cancel} (was {old_status}); soft delete, row retained"
        )
        logger.info(
            f"Loan #{loan.id} cancelled by {request.user.username} "
            f"— balance was ₱{balance_at_cancel}"
        )

        return Response({'message': 'Loan cancelled', 'status': loan.status})


class LoanPaymentsView(APIView):
    permission_classes = [IsAuthenticated, CanManageLoans]

    def get(self, request, pk):
        try:
            loan = EmployeeLoan.objects.get(pk=pk)
        except EmployeeLoan.DoesNotExist:
            logger.warning(f"Loan #{pk} not found for payments list — user={request.user.username}")
            return Response({'error': 'Loan not found'}, status=404)

        payments = loan.payments.select_related('pay_period').all()
        return Response(LoanPaymentSerializer(payments, many=True).data)


class EmployeeLoanListView(APIView):
    permission_classes = [IsAuthenticated, CanManageLoans]

    def get(self, request, employee_id):
        try:
            employee = Employee.objects.get(pk=employee_id)
        except Employee.DoesNotExist:
            logger.warning(f"Employee #{employee_id} not found — user={request.user.username}")
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
            logger.warning(
                f"Reverse attempt — loan #{loan_id} not found "
                f"— user={request.user.username}"
            )
            return Response({'error': 'Loan not found'}, status=404)

        try:
            payment = loan.payments.get(pk=payment_id)
        except LoanPayment.DoesNotExist:
            logger.warning(
                f"Reverse attempt — payment #{payment_id} not found on loan #{loan_id} "
                f"— user={request.user.username}"
            )
            return Response({'error': 'Payment not found'}, status=404)

        if payment.reversed_at:
            logger.warning(
                f"Reverse attempt — payment #{payment_id} already reversed "
                f"— user={request.user.username}"
            )
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

        log_action(
            request.user, 'UPDATE', 'LoanPayment', payment.id,
            f"Reversed ₱{payment.amount} payment on {loan.display_name} — "
            f"balance restored to ₱{loan.balance}"
        )
        logger.info(
            f"Payment #{payment.id} reversed on loan #{loan.id} "
            f"by {request.user.username} — ₱{payment.amount} restored"
        )

        return Response({
            'message': 'Payment reversed',
            'loan': EmployeeLoanSerializer(loan).data,
        })