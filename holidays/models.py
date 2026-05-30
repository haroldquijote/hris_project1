from django.db import models


class Holiday(models.Model):
    class HolidayType(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular Holiday'
        SPECIAL_NON_WORKING = 'SPECIAL_NON_WORKING', 'Special Non-Working Day'

    name = models.CharField(max_length=100)
    date = models.DateField(unique=True)       # one holiday per date
    holiday_type = models.CharField(
        max_length=30,
        choices=HolidayType.choices,
        default=HolidayType.REGULAR,
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage rate e.g. 200 for 200%"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.date})"

    class Meta:
        ordering = ['date']