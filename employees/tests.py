from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from users.models import Profile

from .models import Department, Employee, JobTitle


class EmployeeCRUDTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="admin", password="pass12345")
        profile, _ = Profile.objects.get_or_create(user=self.user)
        profile.role = "HRADMIN"
        profile.can_manage_employees = True
        profile.save()
        self.client.force_authenticate(user=self.user)

        self.department = Department.objects.create(name="Engineering")
        self.job_title = JobTitle.objects.create(title="Software Engineer", department=self.department)

    def employee_payload(self, **overrides):
        data = {
            "company_id": "EMP-001",
            "department": self.department.pk,
            "job_title": self.job_title.pk,
            "employment_status": "REGULAR",
            "date_hired": "2025-01-01",
            "date_of_resignation": None,
            "last_name": "Doe",
            "first_name": "Jane",
            "middle_name": "A",
            "mothers_maiden_name": "Smith",
            "birth_date": "2000-01-01",
            "birth_place": "City",
            "nationality": "Filipino",
            "gender": "F",
            "marital_status": "S",
            "permanent_address": "123 Street",
            "city": "Manila",
            "zip_code": "1000",
            "mobile_no": "09123456789",
            "email": "jane@example.com",
            "tin": "",
            "sss_gsis_no": "",
            "hdmf": "",
            "philhealth": "",
            "drivers_license": "",
            "passport": "",
        }
        data.update(overrides)
        return data

    def create_employee(self, **overrides):
        payload = self.employee_payload(**overrides)
        return Employee.objects.create(
            company_id=payload["company_id"],
            department=self.department,
            job_title=self.job_title,
            employment_status=payload["employment_status"],
            date_hired=payload["date_hired"],
            date_of_resignation=payload["date_of_resignation"],
            last_name=payload["last_name"],
            first_name=payload["first_name"],
            middle_name=payload["middle_name"],
            mothers_maiden_name=payload["mothers_maiden_name"],
            birth_date=payload["birth_date"],
            birth_place=payload["birth_place"],
            nationality=payload["nationality"],
            gender=payload["gender"],
            marital_status=payload["marital_status"],
            permanent_address=payload["permanent_address"],
            city=payload["city"],
            zip_code=payload["zip_code"],
            mobile_no=payload["mobile_no"],
            email=payload["email"],
            tin=payload["tin"],
            sss_gsis_no=payload["sss_gsis_no"],
            hdmf=payload["hdmf"],
            philhealth=payload["philhealth"],
            drivers_license=payload["drivers_license"],
            passport=payload["passport"],
        )

    def test_employee_list_loads(self):
        self.create_employee()
        response = self.client.get(reverse("employee-list"))

        self.assertEqual(response.status_code, 200)
        # works whether or not pagination is on
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertIn("EMP-001", [row["company_id"] for row in results])

    def test_create_employee(self):
        response = self.client.post(reverse("employee-list"), self.employee_payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Employee.objects.filter(company_id="EMP-001").exists())

    def test_create_employee_invalid(self):
        invalid = self.employee_payload(email="")
        response = self.client.post(reverse("employee-list"), invalid, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertFalse(Employee.objects.filter(company_id="EMP-001").exists())

    def test_update_employee(self):
        employee = self.create_employee()
        updated = self.employee_payload(last_name="Smith", company_id="EMP-002", email="smith@example.com")

        response = self.client.put(
            reverse("employee-detail", args=[employee.pk]), updated, format="json"
        )
        employee.refresh_from_db()

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(employee.last_name, "Smith")
        self.assertEqual(employee.company_id, "EMP-002")

    def test_delete_employee(self):
        employee = self.create_employee()

        response = self.client.delete(reverse("employee-detail", args=[employee.pk]))

        self.assertIn(response.status_code, (200, 204))
        self.assertFalse(Employee.objects.filter(pk=employee.pk).exists())

    def test_employee_detail_loads(self):
        employee = self.create_employee()
        response = self.client.get(reverse("employee-detail", args=[employee.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["company_id"], "EMP-001")

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("employee-list"))

        self.assertIn(response.status_code, (401, 403))