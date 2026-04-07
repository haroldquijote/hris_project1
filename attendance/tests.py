from django.test import TestCase
from django.urls import reverse

from employees.models import Department, Employee, JobTitle

from .models import Attendance


class AttendanceCRUDTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="HR")
        self.job_title = JobTitle.objects.create(title="HR Staff", department=self.department)
        self.employee = Employee.objects.create(
            company_id="EMP-ATT-001",
            department=self.department,
            job_title=self.job_title,
            employment_status="REGULAR",
            date_hired="2025-01-01",
            date_of_resignation=None,
            last_name="Reyes",
            first_name="Ana",
            middle_name="",
            mothers_maiden_name="Cruz",
            birth_date="1999-02-02",
            birth_place="Quezon City",
            nationality="Filipino",
            gender="F",
            marital_status="S",
            permanent_address="456 Street",
            city="Quezon City",
            zip_code="1100",
            mobile_no="09999999999",
            email="ana.reyes@example.com",
            tin="",
            sss_gsis_no="",
            hdmf="",
            philhealth="",
            drivers_license="",
            passport="",
        )

    def attendance_payload(self, **overrides):
        data = {
            "employee": self.employee.pk,
            "date": "2026-01-15",
            "time_in": "08:00",
            "time_out": "17:00",
        }
        data.update(overrides)
        return data

    def create_attendance(self, **overrides):
        payload = self.attendance_payload(**overrides)
        return Attendance.objects.create(
            employee=self.employee,
            date=payload["date"],
            time_in=payload["time_in"],
            time_out=payload["time_out"],
        )

    def test_attendance_list_page_loads(self):
        self.create_attendance()
        response = self.client.get(reverse("attendance_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reyes, Ana")

    def test_create_attendance(self):
        response = self.client.post(reverse("attendance_create"), data=self.attendance_payload())

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Attendance.objects.filter(employee=self.employee, date="2026-01-15").exists())

    def test_create_attendance_invalid_form(self):
        invalid = self.attendance_payload(date="")
        response = self.client.post(reverse("attendance_create"), data=invalid)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")

    def test_update_attendance(self):
        attendance = self.create_attendance()
        updated = self.attendance_payload(date="2026-01-16", time_in="09:00", time_out="18:00")

        response = self.client.post(reverse("attendance_update", args=[attendance.pk]), data=updated)
        attendance.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(attendance.date), "2026-01-16")
        self.assertEqual(str(attendance.time_in), "09:00:00")

    def test_delete_attendance(self):
        attendance = self.create_attendance()

        response = self.client.post(reverse("attendance_delete", args=[attendance.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Attendance.objects.filter(pk=attendance.pk).exists())

    def test_attendance_detail_page_loads(self):
        attendance = self.create_attendance()
        response = self.client.get(reverse("attendance_detail", args=[attendance.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance Details")
