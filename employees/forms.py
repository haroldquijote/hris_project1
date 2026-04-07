from django import forms

from .models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = "__all__"
        widgets = {
            "date_hired": forms.DateInput(attrs={"type": "date"}),
            "date_of_resignation": forms.DateInput(attrs={"type": "date"}),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }
