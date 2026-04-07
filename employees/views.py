from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db import models  

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


# ---------- Pagination ----------

class EmployeePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DepartmentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class JobTitlePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class WorkSchedulePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ========== DEPARTMENT VIEWS ==========

class DepartmentListView(APIView):
    """List all departments or create a new department"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/employees/departments/ - List all departments"""
        departments = Department.objects.all()
        
        # Optional: Search by name
        search = request.query_params.get('search', None)
        if search:
            departments = departments.filter(name__icontains=search)
        
        paginator = DepartmentPagination()
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
        try:
            return Department.objects.get(pk=pk)
        except Department.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """GET /api/employees/departments/{id}/ - Get department details"""
        department = self.get_object(pk)
        if not department:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DepartmentSerializer(department)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """PUT /api/employees/departments/{id}/ - Update department"""
        department = self.get_object(pk)
        if not department:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DepartmentSerializer(department, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """DELETE /api/employees/departments/{id}/ - Delete department"""
        department = self.get_object(pk)
        if not department:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if department has employees
        if department.employees.exists():
            return Response(
                {"error": "Cannot delete department with existing employees. Reassign or delete employees first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        department.delete()
        return Response({"message": "Department deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ========== JOB TITLE VIEWS ==========

class JobTitleListView(APIView):
    """List all job titles or create a new job title"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/employees/job-titles/ - List all job titles"""
        job_titles = JobTitle.objects.all()
        
        # Filter by department
        department_id = request.query_params.get('department', None)
        if department_id:
            job_titles = job_titles.filter(department_id=department_id)
        
        # Search by title
        search = request.query_params.get('search', None)
        if search:
            job_titles = job_titles.filter(title__icontains=search)
        
        paginator = JobTitlePagination()
        paginated_job_titles = paginator.paginate_queryset(job_titles, request)
        serializer = JobTitleSerializer(paginated_job_titles, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """POST /api/employees/job-titles/ - Create a new job title"""
        serializer = JobTitleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobTitleDetailView(APIView):
    """Get, update or delete a single job title"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return JobTitle.objects.get(pk=pk)
        except JobTitle.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """GET /api/employees/job-titles/{id}/ - Get job title details"""
        job_title = self.get_object(pk)
        if not job_title:
            return Response({"error": "Job title not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = JobTitleSerializer(job_title)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """PUT /api/employees/job-titles/{id}/ - Update job title"""
        job_title = self.get_object(pk)
        if not job_title:
            return Response({"error": "Job title not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = JobTitleSerializer(job_title, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """DELETE /api/employees/job-titles/{id}/ - Delete job title"""
        job_title = self.get_object(pk)
        if not job_title:
            return Response({"error": "Job title not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if job title has employees
        if job_title.employees.exists():
            return Response(
                {"error": "Cannot delete job title with existing employees. Reassign or delete employees first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job_title.delete()
        return Response({"message": "Job title deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ========== WORK SCHEDULE VIEWS ==========

class WorkScheduleListView(APIView):
    """List all work schedules or create a new work schedule"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/employees/work-schedules/ - List all work schedules"""
        schedules = WorkSchedule.objects.all()
        
        paginator = WorkSchedulePagination()
        paginated_schedules = paginator.paginate_queryset(schedules, request)
        serializer = WorkScheduleSerializer(paginated_schedules, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """POST /api/employees/work-schedules/ - Create a new work schedule"""
        serializer = WorkScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkScheduleDetailView(APIView):
    """Get, update or delete a single work schedule"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return WorkSchedule.objects.get(pk=pk)
        except WorkSchedule.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """GET /api/employees/work-schedules/{id}/ - Get work schedule details"""
        schedule = self.get_object(pk)
        if not schedule:
            return Response({"error": "Work schedule not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WorkScheduleSerializer(schedule)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """PUT /api/employees/work-schedules/{id}/ - Update work schedule"""
        schedule = self.get_object(pk)
        if not schedule:
            return Response({"error": "Work schedule not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WorkScheduleSerializer(schedule, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """DELETE /api/employees/work-schedules/{id}/ - Delete work schedule"""
        schedule = self.get_object(pk)
        if not schedule:
            return Response({"error": "Work schedule not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if schedule is assigned to any employee
        if schedule.employees.exists():
            return Response(
                {"error": "Cannot delete work schedule assigned to employees. Reassign employees first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedule.delete()
        return Response({"message": "Work schedule deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ========== EXISTING EMPLOYEE VIEWS (from before) ==========

class EmployeeListView(APIView):
    """List all employees or create a new employee"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/employees/ - List all employees (paginated)"""
        employees = Employee.objects.all()
        
        # Filter by department
        department_id = request.query_params.get('department', None)
        if department_id:
            employees = employees.filter(department_id=department_id)
        
        # Filter by employment status
        status_filter = request.query_params.get('status', None)
        if status_filter:
            employees = employees.filter(employment_status=status_filter)
        
        # Search by name or company_id
        search = request.query_params.get('search', None)
        if search:
            employees = employees.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(company_id__icontains=search) |
                models.Q(email__icontains=search)
            )
        
        paginator = EmployeePagination()
        paginated_employees = paginator.paginate_queryset(employees, request)
        serializer = EmployeeListSerializer(paginated_employees, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """POST /api/employees/ - Create a new employee"""
        serializer = EmployeeSerializer(data=request.data)
        if serializer.is_valid():
            employee = serializer.save()
            return Response(EmployeeSerializer(employee).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeDetailView(APIView):
    """Get, update or delete a single employee"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return Employee.objects.get(pk=pk)
        except Employee.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """GET /api/employees/{id}/ - Get single employee details"""
        employee = self.get_object(pk)
        if not employee:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """PUT /api/employees/{id}/ - Update entire employee"""
        employee = self.get_object(pk)
        if not employee:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = EmployeeSerializer(employee, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """PATCH /api/employees/{id}/ - Partially update employee"""
        employee = self.get_object(pk)
        if not employee:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = EmployeeSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """DELETE /api/employees/{id}/ - Delete employee"""
        employee = self.get_object(pk)
        if not employee:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        employee.delete()
        return Response({"message": "Employee deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ========== EMPLOYEE SALARY VIEWS ==========

class EmployeeSalaryListView(APIView):
    """List salaries for an employee or create new salary record"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, employee_pk):
        """GET /api/employees/{employee_pk}/salaries/ - List all salaries for an employee"""
        try:
            employee = Employee.objects.get(pk=employee_pk)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        salaries = employee.salaries.all()
        serializer = EmployeeSalarySerializer(salaries, many=True)
        return Response(serializer.data)
    
    def post(self, request, employee_pk):
        """POST /api/employees/{employee_pk}/salaries/ - Create new salary record"""
        try:
            employee = Employee.objects.get(pk=employee_pk)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data.copy()
        data['employee'] = employee.id
        
        serializer = EmployeeSalaryCreateSerializer(data=data)
        if serializer.is_valid():
            salary = serializer.save(created_by=request.user)
            return Response(EmployeeSalarySerializer(salary).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeSalaryDetailView(APIView):
    """Get, update or delete a specific salary record"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return EmployeeSalary.objects.get(pk=pk)
        except EmployeeSalary.DoesNotExist:
            return None
    
    def get(self, request, employee_pk, salary_pk):
        salary = self.get_object(salary_pk)
        if not salary:
            return Response({"error": "Salary record not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if salary.employee.id != int(employee_pk):
            return Response({"error": "Salary record does not belong to this employee"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = EmployeeSalarySerializer(salary)
        return Response(serializer.data)
    
    def put(self, request, employee_pk, salary_pk):
        salary = self.get_object(salary_pk)
        if not salary:
            return Response({"error": "Salary record not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if salary.employee.id != int(employee_pk):
            return Response({"error": "Salary record does not belong to this employee"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = EmployeeSalaryCreateSerializer(salary, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(EmployeeSalarySerializer(salary).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, employee_pk, salary_pk):
        salary = self.get_object(salary_pk)
        if not salary:
            return Response({"error": "Salary record not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if salary.employee.id != int(employee_pk):
            return Response({"error": "Salary record does not belong to this employee"}, status=status.HTTP_400_BAD_REQUEST)
        
        salary.delete()
        return Response({"message": "Salary record deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class CurrentEmployeeSalaryView(APIView):
    """Get current active salary for an employee"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, employee_pk):
        """GET /api/employees/{employee_pk}/salary/current/ - Get current salary"""
        try:
            employee = Employee.objects.get(pk=employee_pk)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        
        current_salary = employee.salaries.filter(end_date__isnull=True).first()
        
        if not current_salary:
            return Response({"message": "No current salary record found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = EmployeeSalarySerializer(current_salary)
        return Response(serializer.data)