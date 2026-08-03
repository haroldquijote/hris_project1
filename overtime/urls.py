from django.urls import path
from . import views

urlpatterns = [
    # Overtime requests
    path('requests/', views.OvertimeRequestListCreateView.as_view(), name='ot-list'),
    path('requests/<int:pk>/', views.OvertimeRequestDetailView.as_view(), name='ot-detail'),
    path('requests/<int:pk>/approve/', views.OvertimeRequestApproveView.as_view(), name='ot-approve'),
    path('requests/<int:pk>/reject/', views.OvertimeRequestRejectView.as_view(), name='ot-reject'),
    path('requests/<int:pk>/cancel/', views.OvertimeRequestCancelView.as_view(), name='ot-cancel'),

    # Configuration
    path('config/', views.OvertimeConfigurationView.as_view(), name='ot-config'),
]