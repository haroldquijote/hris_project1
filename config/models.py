from django.db import models

# Create your models here.
from django.db import models
from simple_history.models import HistoricalRecords


class Holiday(models.Model):

    HOLIDAY_TYPE_CHOICES = [
        ('REGULAR', 'Regular Holiday'),
        ('SPECIAL_NON_WORKING', 'Special Non-Working Holiday'),
        ('SPECIAL_WORKING', 'Special Working Holiday'),
    ]

    name = models.CharField(max_length=200)
    date = models.DateField(unique=True)
    holiday_type = models.CharField(
        max_length=20,
        choices=HOLIDAY_TYPE_CHOICES
    )
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage rate e.g. 200 for 200%"
    )
    is_no_work_no_pay = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    history = HistoricalRecords()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.date}"

    class Meta:
        ordering = ['date']