from rest_framework import serializers
from .models import JobPosting, Candidate


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = [
            'id', 'job_posting', 'name', 'email', 'phone',
            'resume', 'extracted_text', 'similarity_score',
            'matching_keywords',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'extracted_text', 'similarity_score',
            'matching_keywords', 'created_at', 'updated_at'
        ]


class JobPostingSerializer(serializers.ModelSerializer):
    candidates = CandidateSerializer(many=True, read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            'id', 'title', 'department', 'description',
            'required_skills', 'candidates', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']