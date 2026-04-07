from django.contrib import admin

# Register your models here.
from simple_history.admin import SimpleHistoryAdmin

from .models import Holiday


@admin.register(Holiday)
class HolidayAdmin(SimpleHistoryAdmin):
    list_display = ("name", "date", "holiday_type", "rate", "is_no_work_no_pay")
    list_filter = ("holiday_type", "is_no_work_no_pay")
    search_fields = ("name",)
    ordering = ("date",)