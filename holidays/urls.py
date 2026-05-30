from django.urls import path
from . import views

urlpatterns = [
    path('', views.HolidayListCreateView.as_view(), name='holiday-list'),
    path('check/', views.HolidayCheckView.as_view(), name='holiday-check'),
    path('<int:pk>/', views.HolidayDetailView.as_view(), name='holiday-detail'),
]