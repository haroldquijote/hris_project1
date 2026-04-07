from django.shortcuts import get_object_or_404, redirect, render

from .forms import AttendanceForm
from .models import Attendance


def attendance_list(request):
    attendances = Attendance.objects.select_related("employee").all()
    return render(request, "attendance/attendance_list.html", {"attendances": attendances})


def attendance_detail(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    return render(request, "attendance/attendance_detail.html", {"attendance": attendance})


def attendance_create(request):
    if request.method == "POST":
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save()
            return redirect("attendance_detail", pk=attendance.pk)
    else:
        form = AttendanceForm()

    return render(request, "attendance/attendance_form.html", {"form": form, "is_edit": False})


def attendance_update(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)

    if request.method == "POST":
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            attendance = form.save()
            return redirect("attendance_detail", pk=attendance.pk)
    else:
        form = AttendanceForm(instance=attendance)

    return render(request, "attendance/attendance_form.html", {"form": form, "attendance": attendance, "is_edit": True})


def attendance_delete(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)

    if request.method == "POST":
        attendance.delete()
        return redirect("attendance_list")

    return render(request, "attendance/attendance_confirm_delete.html", {"attendance": attendance})
