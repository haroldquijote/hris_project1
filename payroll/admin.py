from django.contrib import admin
from .models import PayPeriod, Payslip

@admin.register(PayPeriod)
class PayPeriodAdmin(admin.ModelAdmin):
    list_display = ['start_date', 'end_date', 'status']

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ['employee', 'pay_period', 'basic_pay', 'allowances_total', 'gross_pay', 'status']
    list_filter = ['pay_period', 'status']