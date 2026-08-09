from django.db import models
from employees.models import Department


class JobPosting(models.Model):
    title = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='job_postings'
    )
    description = models.TextField()
    required_skills = models.TextField(
        blank=True,
        help_text="Comma‑separated list of required skills, e.g. React, Django, PostgreSQL"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Candidate(models.Model):
    class Status(models.TextChoices):
        APPLIED = 'APPLIED', 'Applied'
        SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
        REJECTED = 'REJECTED', 'Rejected'
        HIRED = 'HIRED', 'Hired'

    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name='candidates'
    )
    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    resume = models.FileField(upload_to='resumes/')

    # LLM grading results
    llm_score = models.FloatField(null=True, blank=True, help_text="Score 0–100 from DeepSeek")
    llm_justification = models.TextField(blank=True, help_text="Two‑sentence explanation from the AI")
    anonymized_text = models.TextField(blank=True, help_text="Resume text after anonymisation")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-llm_score']   # rank from highest to lowest

    def __str__(self):
        return self.name or f"Candidate {self.id}"