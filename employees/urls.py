from django.urls import path
from . import views

urlpatterns = [
    # ========== DEPARTMENT URLs ==========
    path('departments/', views.DepartmentListView.as_view(), name='department-list'),
    path('departments/<int:pk>/', views.DepartmentDetailView.as_view(), name='department-detail'),
    
    # ========== JOB TITLE URLs ==========
    path('job-titles/', views.JobTitleListView.as_view(), name='jobtitle-list'),
    path('job-titles/<int:pk>/', views.JobTitleDetailView.as_view(), name='jobtitle-detail'),
    
    # ========== EMPLOYEE URLs ==========
    path('', views.EmployeeListView.as_view(), name='employee-list'),
    path('<int:pk>/', views.EmployeeDetailView.as_view(), name='employee-detail'),
    
    # ========== EMPLOYEE SALARY URLs ==========
    path('<int:employee_pk>/salaries/', views.EmployeeSalaryListView.as_view(), name='employee-salary-list'),
    path('<int:employee_pk>/salaries/<int:salary_pk>/', views.EmployeeSalaryDetailView.as_view(), name='employee-salary-detail'),
    path('<int:employee_pk>/salary/current/', views.CurrentEmployeeSalaryView.as_view(), name='employee-salary-current'),

        # ========== ALLOWANCE TYPE URLs ==========
    path('allowance-types/', views.AllowanceTypeListView.as_view(), name='allowance-type-list'),
    path('allowance-types/<int:pk>/', views.AllowanceTypeDetailView.as_view(), name='allowance-type-detail'),

    # ========== EMPLOYEE ALLOWANCE URLs ==========
    path('<int:employee_pk>/allowances/', views.EmployeeAllowanceListView.as_view(), name='employee-allowance-list'),
    path('<int:employee_pk>/allowances/<int:allowance_pk>/', views.EmployeeAllowanceDetailView.as_view(), name='employee-allowance-detail'),
]
