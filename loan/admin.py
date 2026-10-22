from django.contrib import admin
from .models import EmployeeLoan, LoanPayment


@admin.register(EmployeeLoan)
class EmployeeLoanAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'employee', 'display_name', 'principal_amount',
        'balance', 'months_paid', 'months_remaining', 'status', 'start_date',
    ]
    list_filter = ['loan_type', 'status']
    search_fields = ['employee__company_id', 'employee__first_name', 'employee__last_name']
    readonly_fields = ['balance', 'periods_paid', 'created_at', 'updated_at']


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan', 'pay_period', 'amount', 'balance_after', 'created_at']
    list_filter = ['loan__loan_type']
    search_fields = ['loan__employee__company_id']