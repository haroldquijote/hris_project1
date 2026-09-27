from decimal import Decimal
from .models import (
    SSSContribution, PhilHealthContribution,
    PagIBIGContribution, WithholdingTaxTable
)
from employees.models import EmployeeSalary


def compute_government_deductions(employee, pay_period, gross_pay):
    """
    Returns dict with 'sss', 'philhealth', 'pagibig', 'tax' for the pay period.
    Deductions are full monthly amounts, assigned to the appropriate half:
        - 1st half (1-15): Pag-IBIG + PhilHealth only
        - 2nd half (16-EOM): SSS + Tax only
    """
    # 1. Monthly equivalent salary
    active_salary = EmployeeSalary.objects.filter(
        employee=employee, end_date__isnull=True
    ).first()
    if not active_salary:
        return {'sss': Decimal('0'), 'philhealth': Decimal('0'),
                'pagibig': Decimal('0'), 'tax': Decimal('0')}

    monthly_salary = Decimal(active_salary.base_salary)

    # ---------- Compute monthly contributions (full) ----------
    # SSS
    sss_row = SSSContribution.objects.filter(
        salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
    ).first()
    sss_monthly = sss_row.employee_share if sss_row else Decimal('0')

    # PhilHealth
    phil_row = PhilHealthContribution.objects.filter(
        salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
    ).first()
    if phil_row:
        salary_for_phil = min(max(monthly_salary, Decimal('10000')), Decimal('100000'))
        phil_monthly = round(salary_for_phil * phil_row.employee_share_rate, 2)
    else:
        phil_monthly = Decimal('0')

    # Pag-IBIG
    pagibig_row = PagIBIGContribution.objects.filter(
        salary_from__lte=monthly_salary, salary_to__gte=monthly_salary
    ).first()
    if pagibig_row:
        if pagibig_row.employee_share < Decimal('1'):   # a rate
            base_for_pagibig = min(monthly_salary, Decimal('10000'))
            if pagibig_row.employee_share == Decimal('0.01'):
                pagibig_monthly = min(base_for_pagibig * Decimal('0.01'), Decimal('200'))
            else:
                pagibig_monthly = min(base_for_pagibig * Decimal('0.02'), Decimal('200'))
        else:
            pagibig_monthly = pagibig_row.employee_share   # fixed amount
    else:
        pagibig_monthly = Decimal('0')

    # ---------- Withholding Tax (monthly table, filtered by tax status) ----------
    monthly_gross = gross_pay * 2   # approximate (semi-monthly gross -> monthly)
    taxable_income = monthly_gross - sss_monthly - phil_monthly - pagibig_monthly
    if taxable_income < 0:
        taxable_income = Decimal('0')

    tax_monthly = Decimal('0')
    tax_row = WithholdingTaxTable.objects.filter(
        tax_status=employee.tax_status,
        compensation_from__lte=taxable_income,
        compensation_to__gte=taxable_income,
    ).first()
    if tax_row:
        base = Decimal(tax_row.base_tax)
        rate = Decimal(tax_row.rate_above)
        exempt = Decimal(tax_row.exemption_amount)
        tax_monthly = base + (taxable_income - exempt) * rate
        if tax_monthly < 0:
            tax_monthly = Decimal('0')

    # ---------- Assign deductions based on pay period ----------
    is_first_half = pay_period.start_date.day == 1

    if is_first_half:
        return {
            'sss': Decimal('0'),
            'philhealth': phil_monthly,      # full month
            'pagibig': pagibig_monthly,      # full month
            'tax': Decimal('0'),
        }
    else:
        return {
            'sss': sss_monthly,              # full month
            'philhealth': Decimal('0'),
            'pagibig': Decimal('0'),
            'tax': tax_monthly,              # full month
        }