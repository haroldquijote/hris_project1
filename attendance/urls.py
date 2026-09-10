from django.urls import path
from . import views

urlpatterns = [
    # Attendance records
    path('', views.AttendanceListCreateView.as_view(), name='attendance-list'),
    path('<int:pk>/', views.AttendanceDetailView.as_view(), name='attendance-detail'),
    path('import/', views.AttendanceImportView.as_view(), name='attendance-import'),

    # Work schedules (now under attendance)
    path('work-schedules/', views.WorkScheduleListCreateView.as_view(), name='workschedule-list'),
    path('work-schedules/<int:pk>/', views.WorkScheduleDetailView.as_view(), name='workschedule-detail'),
]