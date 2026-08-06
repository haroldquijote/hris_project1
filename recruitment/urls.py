from django.urls import path
from . import views

urlpatterns = [
    path('jobs/', views.JobPostingListCreateView.as_view(), name='job-list'),
    path('jobs/<int:pk>/', views.JobPostingDetailView.as_view(), name='job-detail'),
    path('jobs/<int:job_id>/upload/', views.CandidateUploadView.as_view(), name='candidate-upload'),
    path('jobs/<int:job_id>/rerank/', views.RerankCandidatesView.as_view(), name='candidate-rerank'),
    path('candidates/<int:pk>/', views.CandidateDetailView.as_view(), name='candidate-detail'),
]