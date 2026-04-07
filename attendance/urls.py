from django.urls import path

from . import views

urlpatterns = [
    path("attendance/", views.attendance_list, name="attendance_list"),
    path("attendance/new/", views.attendance_create, name="attendance_create"),
    path("attendance/<int:pk>/", views.attendance_detail, name="attendance_detail"),
    path("attendance/<int:pk>/edit/", views.attendance_update, name="attendance_update"),
    path("attendance/<int:pk>/delete/", views.attendance_delete, name="attendance_delete"),
]
