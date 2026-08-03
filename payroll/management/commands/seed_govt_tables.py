from django.core.management.base import BaseCommand
from payroll.models import (
    SSSContribution, PhilHealthContribution,
    PagIBIGContribution, WithholdingTaxTable
)

class Command(BaseCommand):
    help = 'Seed the government contribution tables with 2026 official rates'

    def handle(self, *args, **options):
        # Clear old data
        SSSContribution.objects.all().delete()
        PhilHealthContribution.objects.all().delete()
        PagIBIGContribution.objects.all().delete()
        WithholdingTaxTable.objects.all().delete()

        # ----------------------------------------------------------------------
        # SSS Contribution Table (2026)
        # MSC ₱5,000–₱35,000 in ₱500 steps, employee share = 5% of MSC
        # ----------------------------------------------------------------------
        sss_data = []
        # Generate MSC from 5000 to 35000, step 500.
        # Each bracket: salary_from = msc - 250 (if possible), salary_to = msc + 249.99
        # For simplicity, we use the exact MSC value as the basis,
        # but the practical lookup will be: round salary to nearest 500, clip to 5k-35k.
        # We'll store one row per MSC with a salary range that covers that MSC.
        for msc in range(5000, 35500, 500):
            lower = msc - 250 if msc > 5000 else 0
            upper = msc + 249.99
            employee_share = msc * 0.05
            sss_data.append((lower, upper, msc, employee_share))

        for row in sss_data:
            SSSContribution.objects.create(
                salary_from=row[0],
                salary_to=row[1],
                monthly_salary_credit=row[2],
                employee_share=row[3]
            )

        # ----------------------------------------------------------------------
        # PhilHealth Contribution Table (2026)
        # 5% total, 2.5% employee share, floor ₱10,000, ceiling ₱100,000
        # ----------------------------------------------------------------------
        PhilHealthContribution.objects.create(
            salary_from=0,
            salary_to=10000.00,
            premium_rate=0.05,
            employee_share_rate=0.025
        )
        PhilHealthContribution.objects.create(
            salary_from=10000.01,
            salary_to=100000.00,
            premium_rate=0.05,
            employee_share_rate=0.025
        )
        PhilHealthContribution.objects.create(
            salary_from=100000.01,
            salary_to=999999.99,
            premium_rate=0.05,
            employee_share_rate=0.025
        )

        # ----------------------------------------------------------------------
        # Pag-IBIG Contribution Table (2026)
        # Employee share: 1% if salary ≤ ₱1,500, else 2%, capped at ₱200.
        # Base salary for contribution capped at ₱10,000.
        # ----------------------------------------------------------------------
        PagIBIGContribution.objects.create(
            salary_from=0,
            salary_to=1500.00,
            employee_share=0.01   # 1% (but actual amount will be calculated)
        )
        PagIBIGContribution.objects.create(
            salary_from=1500.01,
            salary_to=10000.00,
            employee_share=0.02   # 2%
        )
        PagIBIGContribution.objects.create(
            salary_from=10000.01,
            salary_to=999999.99,
            employee_share=200.00  # max ₱200
        )

        # ----------------------------------------------------------------------
        # Withholding Tax Table (Semi‑Monthly, S/0)
        # ----------------------------------------------------------------------
        tax_data = [
            (0, 10417, 0, 0, 0),
            (10417, 16666, 0, 0.15, 10417),
            (16667, 33332, 937.50, 0.20, 16667),
            (33333, 83332, 4270.70, 0.25, 33333),
            (83333, 333332, 16770.70, 0.30, 83333),
            (333333, 9999999, 91770.70, 0.35, 333333),
        ]
        for row in tax_data:
            WithholdingTaxTable.objects.create(
                compensation_from=row[0],
                compensation_to=row[1],
                base_tax=row[2],
                rate_above=row[3],
                exemption_amount=row[4]
            )

        self.stdout.write(self.style.SUCCESS('Government tables seeded successfully.'))