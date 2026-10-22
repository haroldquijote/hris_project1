from decimal import Decimal
from django.db import transaction

from .models import EmployeeLoan, LoanPayment


@transaction.atomic
def apply_loans_to_payslip(payslip, pay_period):
    """
    Deduct active loan payments for this pay period from the payslip.

    Idempotent — if a payment already exists for (loan, pay_period), uses
    the existing amount and does NOT touch the balance.
    """
    total = Decimal('0.00')

    active_loans = EmployeeLoan.objects.filter(
        employee=payslip.employee,
        status=EmployeeLoan.Status.ACTIVE,
        start_date__lte=pay_period.start_date,
    )

    for loan in active_loans:
        # Idempotency check
        existing = LoanPayment.objects.filter(
            loan=loan, pay_period=pay_period, reversed_at__isnull=True,
        ).first()

        if existing:
            total += existing.amount
            continue

        # Fresh payment for this period
        amount = loan.calculate_next_payment()
        if amount <= Decimal('0.00'):
            continue

        balance_before = loan.balance
        balance_after = balance_before - amount

        LoanPayment.objects.create(
            loan=loan,
            pay_period=pay_period,
            payslip=payslip,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
        )

        loan.balance = balance_after
        loan.periods_paid += 1
        if balance_after <= Decimal('0.01'):
            loan.balance = Decimal('0.00')
            loan.status = EmployeeLoan.Status.COMPLETED
        loan.save()

        total += amount

    payslip.loan_deduction_total = total
    payslip.save(update_fields=['loan_deduction_total'])
    return total