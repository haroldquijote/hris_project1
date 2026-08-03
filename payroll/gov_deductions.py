from decimal import Decimal
from .models import SSSContribution, PhilHealthContribution, PagIBIGContribution
from employees.models import EmployeeSalary


# Monthly withholding tax table (2026, S/0)
MONTHLY_TAX_BRACKETS = [
    (0, 20833, 0, 0, 0),
    (20833, 33332, 0, 0.15, 20833),
    (33333, 66666, 1875, 0.20, 33333),
    (66667, 166666, 8541.80, 0.25, 66667),
    (166667, 666666, 33541.80, 0.30, 166667),
    (666667, 99999999, 183541.80, 0.35, 666667),
]


def compute_government_deductions(employee, pay_period, gross_pay):
    """
    Returns dict with 'sss', 'philhealth', 'pagibig', 'tax' for the pay period.
    Deductions are full monthly amounts, assigned to the appropriate half:
        - 1st half (1-15): Pag-IBIG + PhilHealth only
        - 2nd half (16-EOM): SSS + Tax only
    """
    active_salary = EmployeeSalary.objects.filter(
        employee=employee, end_date__isnull=True
    ).first()
    if not active_salary:
        return {'sss': Decimal('0'), 'philhealth': Decimal('0'),
                'pagibig': Decimal('0'), 'tax': Decimal('0')}

    monthly_salary = Decimal(active_salary.base_salary)

    # ---------- Full monthly contributions ----------
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

    # Withholding Tax (monthly table)
    monthly_gross = gross_pay * 2   # approximate
    taxable_income = monthly_gross - sss_monthly - phil_monthly - pagibig_monthly
    if taxable_income < 0:
        taxable_income = Decimal('0')

    tax_monthly = Decimal('0')
    for bracket in MONTHLY_TAX_BRACKETS:
        from_amount, to_amount, base, rate, exempt = bracket
        if taxable_income >= from_amount and taxable_income <= to_amount:
            base = Decimal(base)
            rate = Decimal(rate)
            exempt = Decimal(exempt)
            tax_monthly = base + (taxable_income - exempt) * rate
            if tax_monthly < 0:
                tax_monthly = Decimal('0')
            break

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