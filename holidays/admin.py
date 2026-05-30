from django.contrib import admin
from .models import Holiday

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'holiday_type', 'percentage']
    list_filter = ['holiday_type', 'date']
    search_fields = ['name']