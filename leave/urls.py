from django.urls import path
from . import views

urlpatterns = [
    # Configuration
    path('config/', views.LeaveConfigurationView.as_view(), name='leave-config'),

    # Leave types
    path('types/', views.LeaveTypeListCreateView.as_view(), name='leavetype-list'),
    path('types/<int:pk>/', views.LeaveTypeDetailView.as_view(), name='leavetype-detail'),

    # Leave requests
    path('requests/', views.LeaveRequestListCreateView.as_view(), name='leaverequest-list'),
    path('requests/<int:pk>/', views.LeaveRequestDetailView.as_view(), name='leaverequest-detail'),

    # Leave actions
    path('requests/<int:pk>/approve/', views.LeaveRequestApproveView.as_view(), name='leaverequest-approve'),
    path('requests/<int:pk>/reject/', views.LeaveRequestRejectView.as_view(), name='leaverequest-reject'),
    path('requests/<int:pk>/cancel/', views.LeaveRequestCancelView.as_view(), name='leaverequest-cancel'),

    # Balance & reports
    path('balance/', views.EmployeeBalanceView.as_view(), name='leave-balance'),
    path('current/', views.CurrentLeavesView.as_view(), name='leave-current'),
    path('employee/<int:employee_id>/history/', views.EmployeeLeaveHistoryView.as_view(), name='leave-history'),

    # Adjustments
    path('adjustments/', views.LeaveAdjustmentListCreateView.as_view(), name='leave-adjustments'),

    # Admin actions
    path('generate-grants/', views.GenerateAnnualGrantsView.as_view(), name='generate-grants'),
]