from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
import os
import logging

from .models import JobPosting, Candidate
from .serializers import JobPostingSerializer, CandidateSerializer
from .ai import extract_text, compute_matching_keywords

logger = logging.getLogger(__name__)


class JobPostingListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jobs = JobPosting.objects.prefetch_related('candidates').all()
        serializer = JobPostingSerializer(jobs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = JobPostingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobPostingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(JobPosting.objects.prefetch_related('candidates'), pk=pk)

    def get(self, request, pk):
        job = self.get_object(pk)
        serializer = JobPostingSerializer(job)
        return Response(serializer.data)

    def put(self, request, pk):
        job = self.get_object(pk)
        serializer = JobPostingSerializer(job, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        job = self.get_object(pk)
        # Delete associated resume files
        for candidate in job.candidates.all():
            if candidate.resume and os.path.isfile(candidate.resume.path):
                os.remove(candidate.resume.path)
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, job_id):
        job = get_object_or_404(JobPosting, pk=job_id)
        files = request.FILES.getlist('resumes')
        if not files:
            return Response({'error': 'No resume files provided.'}, status=400)

        # Validate file types
        allowed_extensions = {'.pdf', '.docx'}
        for file in files:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                return Response(
                {'error': f'Unsupported file type "{ext}". Only PDF and DOCX files are accepted.'},
                status=status.HTTP_400_BAD_REQUEST
                )
    # -------------------------------------------------
    
        created = []
        with transaction.atomic():
            for file in files:
                candidate = Candidate.objects.create(
                    job_posting=job,
                    resume=file,
                    name=file.name   # placeholder, HR can rename later
                )
                created.append(candidate)

        # Extract text & compute explainable scores
        for candidate in created:
            try:
                text = extract_text(candidate.resume.path)
                candidate.extracted_text = text
                if text.strip():
                    score, matching_kw = compute_matching_keywords(
                        job.description,
                        job.required_skills or '',
                        text
                    )
                    candidate.similarity_score = score
                    candidate.matching_keywords = matching_kw
                else:
                    candidate.similarity_score = 0.0
                    candidate.matching_keywords = {}
                candidate.save()
            except Exception as e:
                logger.exception("Scoring failed")
                candidate.similarity_score = 0.0
                candidate.matching_keywords = {}
                candidate.save()

        # Return all candidates for this job, ordered by score
        job.refresh_from_db()
        serializer = CandidateSerializer(job.candidates.all(), many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CandidateDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Candidate, pk=pk)

    def get(self, request, pk):
        candidate = self.get_object(pk)
        serializer = CandidateSerializer(candidate)
        return Response(serializer.data)

    def patch(self, request, pk):
        candidate = self.get_object(pk)
        serializer = CandidateSerializer(candidate, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        candidate = self.get_object(pk)
        if candidate.resume and os.path.isfile(candidate.resume.path):
            os.remove(candidate.resume.path)
        candidate.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RerankCandidatesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        job = get_object_or_404(JobPosting, pk=job_id)
        candidates = job.candidates.all()
        count = 0
        for candidate in candidates:
            if candidate.extracted_text.strip():
                score, matching_kw = compute_matching_keywords(
                    job.description,
                    job.required_skills or '',
                    candidate.extracted_text
                )
                candidate.similarity_score = score
                candidate.matching_keywords = matching_kw
                candidate.save()
                count += 1
        return Response({'message': f'Re‑ranked {count} candidates.'})