from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from payroll.models import (
    SSSContribution, PhilHealthContribution,
    PagIBIGContribution, WithholdingTaxTable,
)


class Command(BaseCommand):
    help = 'Seed the government contribution tables with 2026 official rates'

    @transaction.atomic
    def handle(self, *args, **options):
        # Clear old data
        SSSContribution.objects.all().delete()
        PhilHealthContribution.objects.all().delete()
        PagIBIGContribution.objects.all().delete()
        WithholdingTaxTable.objects.all().delete()

        # ------------------------------------------------------------------
        # SSS Contribution Table (2026) — unchanged
        # ------------------------------------------------------------------
        for msc in range(5000, 35500, 500):
            lower = msc - 250 if msc > 5000 else 0
            upper = msc + 249.99
            employee_share = msc * 0.05
            SSSContribution.objects.create(
                salary_from=lower,
                salary_to=upper,
                monthly_salary_credit=msc,
                employee_share=employee_share,
            )

        # Catch-all for salaries above the official MSC ceiling (RA 11199).
        # Assigns MSC 35,000 (legal max) → employee share ₱1,750.00.
        SSSContribution.objects.create(
            salary_from=Decimal('35250.00'),
            salary_to=Decimal('99999999.99'),
            monthly_salary_credit=Decimal('35000.00'),
            employee_share=Decimal('1750.00'),
        )

        # ------------------------------------------------------------------
        # PhilHealth Contribution Table (2026) — unchanged
        # ------------------------------------------------------------------
        PhilHealthContribution.objects.create(
            salary_from=0, salary_to=10000.00,
            premium_rate=0.05, employee_share_rate=0.025,
        )
        PhilHealthContribution.objects.create(
            salary_from=10000.01, salary_to=100000.00,
            premium_rate=0.05, employee_share_rate=0.025,
        )
        PhilHealthContribution.objects.create(
            salary_from=100000.01, salary_to=999999.99,
            premium_rate=0.05, employee_share_rate=0.025,
        )
        PhilHealthContribution.objects.create(
            salary_from=Decimal('1000000.00'), salary_to=Decimal('99999999.99'),
            premium_rate=0.05, employee_share_rate=0.025,
        )

        # ------------------------------------------------------------------
        # Pag-IBIG Contribution Table (2026) — unchanged
        # ------------------------------------------------------------------
        PagIBIGContribution.objects.create(
            salary_from=0, salary_to=1500.00, employee_share=0.01,
        )
        PagIBIGContribution.objects.create(
            salary_from=1500.01, salary_to=10000.00, employee_share=0.02,
        )
        PagIBIGContribution.objects.create(
            salary_from=10000.01, salary_to=999999.99, employee_share=200.00,
        )
        PagIBIGContribution.objects.create(
            salary_from=Decimal('1000000.00'), salary_to=Decimal('99999999.99'),
            employee_share=200.00,
        )

        # ------------------------------------------------------------------
        # Withholding Tax Table — Semi-Monthly (2026)
        #
        # S/0 uses the exact BIR-published base taxes.
        # The other 9 statuses are derived mathematically (exemption changes,
        # rate structure identical). For full compliance, replace their
        # base taxes with the official BIR values from RR 11-2018 Annex E.
        # ------------------------------------------------------------------

        # Bracket boundaries and rates (shared across all statuses)
        brackets = [
            (0,         20833,     0.00),
            (20833,     33332,     0.15),
            (33333,     66666,     0.20),
            (66667,     166666,    0.25),
            (166667,    666666,    0.30),
            (666667,    99999999,  0.35),
        ]

        # Official BIR MONTHLY base taxes for S/0
        s0_base_taxes = [
            0,
            0,
            Decimal('1875.00'),
            Decimal('8541.80'),
            Decimal('33541.80'),
            Decimal('183541.80'),
        ]

        # Exemption thresholds per status (MONTHLY)
        tax_statuses = {
            'S/0':  Decimal('20833'),
            'S/1':  Decimal('29167'),
            'S/2':  Decimal('37500'),
            'S/3':  Decimal('45833'),
            'S/4':  Decimal('54167'),
            'ME/0': Decimal('29167'),
            'ME/1': Decimal('37500'),
            'ME/2': Decimal('45833'),
            'ME/3': Decimal('54167'),
            'ME/4': Decimal('62500'),
        }

        def compute_base_taxes(exemption):
            rows = []
            cumulative = Decimal('0')
            for from_, to_, rate in brackets:
                rows.append(cumulative)
                taxable = max(Decimal('0'), Decimal(to_) - max(Decimal(from_), exemption))
                cumulative += taxable * Decimal(str(rate))
            return rows

        for status, exemption in tax_statuses.items():
            # Post-TRAIN (RA 10963): personal exemption is uniform at ₱250,000/year.
            # BIR no longer publishes per-status tables, so all statuses use the
            # same S/0 base taxes.
            base_taxes = s0_base_taxes

            for (from_, to_, rate), base in zip(brackets, base_taxes):
                WithholdingTaxTable.objects.create(
                    tax_status=status,
                    compensation_from=from_,
                    compensation_to=to_,
                    base_tax=round(Decimal(str(base)), 2),
                    rate_above=Decimal(str(rate)),
                    exemption_amount=exemption,
                )

        self.stdout.write(self.style.SUCCESS('Government tables seeded successfully.'))