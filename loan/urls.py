from django.urls import path
from .views import (
    LoanListCreateView, LoanDetailView, LoanPaymentsView,
    EmployeeLoanListView, LoanPaymentReverseView,
)
urlpatterns = [
    path('', LoanListCreateView.as_view(), name='loan-list'),
    path('<int:pk>/', LoanDetailView.as_view(), name='loan-detail'),
    path('<int:pk>/payments/', LoanPaymentsView.as_view(), name='loan-payments'),
    path('employee/<int:employee_id>/', EmployeeLoanListView.as_view(), name='employee-loans'),
    path('<int:loan_id>/payments/<int:payment_id>/reverse/',
         LoanPaymentReverseView.as_view(), name='loan-payment-reverse'),
]