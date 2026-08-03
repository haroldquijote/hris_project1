from django.urls import path
from . import views

urlpatterns = [
    # Pay Periods
    path('periods/', views.PayPeriodListCreateView.as_view(), name='payperiod-list'),
    path('periods/<int:pk>/', views.PayPeriodDetailView.as_view(), name='payperiod-detail'),
    path('periods/<int:pk>/compute/', views.ComputeGrossPayView.as_view(), name='payperiod-compute'),
    path('periods/<int:pk>/lock/', views.PayPeriodLockView.as_view(), name='payperiod-lock'),
    path('periods/<int:pk>/unlock/', views.PayPeriodUnlockView.as_view(), name='payperiod-unlock'),

    # Payslips
    path('payslips/', views.PayslipListView.as_view(), name='payslip-list'),
    path('payslips/<int:pk>/', views.PayslipDetailView.as_view(), name='payslip-detail'),
    path('payslips/<int:payslip_id>/adjustments/', views.PayslipAdjustmentListCreateView.as_view(), name='payslip-adjustments'),

    # Daily breakdown
    path('payslips/<int:payslip_id>/details/', views.PayslipDailyDetailView.as_view(), name='payslip-daily-details'),

    # Storing Company Logo
    path('company-settings/', views.CompanySettingsView.as_view(), name='company-settings'),

    # for Payroll Register 
    path('reports/register/csv/', views.PayrollRegisterCSVView.as_view(), name='payroll-register-csv'),

    # for goverment remittance 
    path('reports/sss/csv/', views.SSSRemittanceCSVView.as_view(), name='sss-remittance-csv'),
    path('reports/philhealth/csv/', views.PhilHealthRemittanceCSVView.as_view(), name='philhealth-remittance-csv'),
    path('reports/pagibig/csv/', views.PagIBIGRemittanceCSVView.as_view(), name='pagibig-remittance-csv'),
    path('reports/bir/csv/', views.BIRRemittanceCSVView.as_view(), name='bir-remittance-csv'),
]       