from django.shortcuts import get_object_or_404
from django.db import models
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Employee, EmployeeSalary, Department, JobTitle, WorkSchedule
from .serializers import (
    EmployeeSerializer,
    EmployeeListSerializer,
    EmployeeSalarySerializer,
    EmployeeSalaryCreateSerializer,
    DepartmentSerializer,
    JobTitleSerializer,
    WorkScheduleSerializer,
)


# ================================================================
# PAGINATION
# ================================================================
# IMPROVEMENT ① : One pagination class for all views.
# Previously we had four identical classes – now all views
# use the same StandardPagination.
# ================================================================
class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ================================================================
# DEPARTMENT VIEWS
# ================================================================

class DepartmentListView(APIView):
    """List all departments or create a new department"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """GET /api/employees/departments/ - List all departments"""
        departments = Department.objects.all()

        # Optional search by name
        search = request.query_params.get('search', None)
        if search:
            departments = departments.filter(name__icontains=search)

        paginator = StandardPagination()
        paginated_departments = paginator.paginate_queryset(departments, request)
        serializer = DepartmentSerializer(paginated_departments, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """POST /api/employees/departments/ - Create a new department"""
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DepartmentDetailView(APIView):
    """Get, update or delete a single department"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        # IMPROVEMENT ② : get_object_or_404 replaces manual try/except.
        # DRF automatically returns a JSON 404 response.
        return get_object_or_404(Department, pk=pk)

    def get(self, request, pk):
        department = self.get_object(pk)
        serializer = DepartmentSerializer(department)
        return Response(serializer.data)

    def put(self, request, pk):
        department = self.get_object(pk)
        serializer = DepartmentSerializer(department, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        department = self.get_object(pk)
        # Protection: cannot delete a department that still has employees
        if department.employees.exists():
            return Response(
                {"error": "Cannot delete department with existing employees. Reassign or delete employees first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        department.delete()
        return Response({"message": "Department deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ================================================================
# JOB TITLE VIEWS
# ================================================================

class JobTitleListView(APIView):
    """List all job titles or create a new job title"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        job_titles = JobTitle.objects.all()

        # Filter by department
        department_id = request.query_params.get('department', None)
        if department_id:
            job_titles = job_titles.filter(department_id=department_id)

        # Search by title
        search = request.query_params.get('search', None)
        if search:
            job_titles = job_titles.filter(title__icontains=search)

        paginator = StandardPagination()
        paginated_job_titles = paginator.paginate_queryset(job_titles, request)
        serializer = JobTitleSerializer(paginated_job_titles, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = JobTitleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobTitleDetailView(APIView):
    """Get, update or delete a single job title"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(JobTitle, pk=pk)

    def get(self, request, pk):
        job_title = self.get_object(pk)
        serializer = JobTitleSerializer(job_title)
        return Response(serializer.data)

    def put(self, request, pk):
        job_title = self.get_object(pk)
        serializer = JobTitleSerializer(job_title, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        job_title = self.get_object(pk)
        if job_title.employees.exists():
            return Response(
                {"error": "Cannot delete job title with existing employees. Reassign or delete employees first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        job_title.delete()
        return Response({"message": "Job title deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ================================================================
# WORK SCHEDULE VIEWS
# ================================================================

class WorkScheduleListView(APIView):
    """List all work schedules or create a new work schedule"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        schedules = WorkSchedule.objects.all()
        paginator = StandardPagination()
        paginated_schedules = paginator.paginate_queryset(schedules, request)
        serializer = WorkScheduleSerializer(paginated_schedules, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = WorkScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkScheduleDetailView(APIView):
    """Get, update or delete a single work schedule"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(WorkSchedule, pk=pk)

    def get(self, request, pk):
        schedule = self.get_object(pk)
        serializer = WorkScheduleSerializer(schedule)
        return Response(serializer.data)

    def put(self, request, pk):
        schedule = self.get_object(pk)
        serializer = WorkScheduleSerializer(schedule, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        schedule = self.get_object(pk)
        if schedule.employees.exists():
            return Response(
                {"error": "Cannot delete work schedule assigned to employees. Reassign employees first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        schedule.delete()
        return Response({"message": "Work schedule deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ================================================================
# EMPLOYEE VIEWS
# ================================================================

class EmployeeListView(APIView):
    """List all employees or create a new employee"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employees = Employee.objects.all()

        # Filter by department
        department_id = request.query_params.get('department', None)
        if department_id:
            employees = employees.filter(department_id=department_id)

        # Filter by employment status
        status_filter = request.query_params.get('status', None)
        if status_filter:
            employees = employees.filter(employment_status=status_filter)

        # Search by name, company ID or email
        search = request.query_params.get('search', None)
        if search:
            employees = employees.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(company_id__icontains=search) |
                models.Q(email__icontains=search)
            )

        paginator = StandardPagination()
        paginated_employees = paginator.paginate_queryset(employees, request)
        serializer = EmployeeListSerializer(paginated_employees, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = EmployeeSerializer(data=request.data)
        if serializer.is_valid():
            employee = serializer.save()
            return Response(EmployeeSerializer(employee).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeDetailView(APIView):
    """Get, update, or delete a single employee"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Employee, pk=pk)

    def get(self, request, pk):
        employee = self.get_object(pk)
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data)

    def put(self, request, pk):
        employee = self.get_object(pk)
        serializer = EmployeeSerializer(employee, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        employee = self.get_object(pk)
        serializer = EmployeeSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        employee = self.get_object(pk)
        employee.delete()
        return Response({"message": "Employee deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ================================================================
# EMPLOYEE SALARY VIEWS
# ================================================================

class EmployeeSalaryListView(APIView):
    """List salaries for an employee or create a new salary record"""
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_pk):
        # IMPROVEMENT ② : get_object_or_404 applied here too
        employee = get_object_or_404(Employee, pk=employee_pk)
        salaries = employee.salaries.all()
        serializer = EmployeeSalarySerializer(salaries, many=True)
        return Response(serializer.data)

    def post(self, request, employee_pk):
        employee = get_object_or_404(Employee, pk=employee_pk)
        data = request.data.copy()
        data['employee'] = employee.id

        serializer = EmployeeSalaryCreateSerializer(data=data)
        if serializer.is_valid():
            salary = serializer.save(employee=employee, created_by=request.user)
            return Response(EmployeeSalarySerializer(salary).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeSalaryDetailView(APIView):
    """Get, update or delete a specific salary record"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(EmployeeSalary, pk=pk)

    def get(self, request, employee_pk, salary_pk):
        salary = self.get_object(salary_pk)
        # Ensure salary really belongs to the employee in the URL
        if salary.employee.id != int(employee_pk):
            return Response(
                {"error": "Salary record does not belong to this employee"},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = EmployeeSalarySerializer(salary)
        return Response(serializer.data)

    def put(self, request, employee_pk, salary_pk):
        salary = self.get_object(salary_pk)
        if salary.employee.id != int(employee_pk):
            return Response(
                {"error": "Salary record does not belong to this employee"},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = EmployeeSalaryCreateSerializer(salary, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(EmployeeSalarySerializer(salary).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, employee_pk, salary_pk):
        salary = self.get_object(salary_pk)
        if salary.employee.id != int(employee_pk):
            return Response(
                {"error": "Salary record does not belong to this employee"},
                status=status.HTTP_400_BAD_REQUEST
            )
        salary.delete()
        return Response(
            {"message": "Salary record deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


class CurrentEmployeeSalaryView(APIView):
    """Get current active salary for an employee"""
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_pk):
        employee = get_object_or_404(Employee, pk=employee_pk)
        current_salary = employee.salaries.filter(end_date__isnull=True).first()

        if not current_salary:
            return Response(
                {"message": "No current salary record found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = EmployeeSalarySerializer(current_salary)
        return Response(serializer.data)