from django.apps import AppConfig
from django.db import connection


class LeaveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leave'

    