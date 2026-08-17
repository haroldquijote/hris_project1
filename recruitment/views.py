from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
import os
import logging
from .anonymizer import anonymize_text
from .llm_grader import grade_resume
from .text_extractor import extract_text
from users.permissions import CanDeleteRecords
from .models import JobPosting, Candidate
from .serializers import JobPostingSerializer, CandidateSerializer
from audit.utils import log_action


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
            job = serializer.save()
            log_action(request.user, 'CREATE', 'JobPosting', job.id, f"Created job posting '{job.title}'")
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
            log_action(request.user, 'UPDATE', 'JobPosting', job.id, f"Updated job posting '{job.title}'")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self.permission_classes = [IsAuthenticated, CanDeleteRecords]
        self.check_permissions(request)
        job = self.get_object(pk)
        # Delete associated resume files
        for candidate in job.candidates.all():
            if candidate.resume and os.path.isfile(candidate.resume.path):
                os.remove(candidate.resume.path)
        log_action(request.user, 'DELETE', 'JobPosting', job.id, f"Deleted job posting '{job.title}'")
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

        created = []
        with transaction.atomic():
            for file in files:
                candidate = Candidate.objects.create(
                    job_posting=job,
                    resume=file,
                    name=file.name
                )
                created.append(candidate)

        # Anonymize and grade
        for candidate in created:
            try:
                raw_text = extract_text(candidate.resume.path)
                if raw_text.strip():
                    anon_text = anonymize_text(raw_text)
                    candidate.anonymized_text = anon_text

                    result = grade_resume(job.description, anon_text)
                    if result and 'score' in result and 'justification' in result:
                        candidate.llm_score = float(result['score'])
                        candidate.llm_justification = result['justification']
                    else:
                        candidate.llm_score = 0.0
                        candidate.llm_justification = "AI scoring failed – please review manually."
                else:
                    candidate.anonymized_text = ''
                    candidate.llm_score = 0.0
                    candidate.llm_justification = "No text could be extracted from the resume."
                candidate.save()
            except Exception as e:
                logger.exception("Candidate processing failed")
                candidate.anonymized_text = ''
                candidate.llm_score = 0.0
                candidate.llm_justification = "Error during processing."
                candidate.save()
            log_action(request.user, 'CREATE', 'Candidate', candidate.id, f"Uploaded resume for {job.title}")

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
            log_action(request.user, 'UPDATE', 'Candidate', candidate.id, f"Updated candidate {candidate.name}")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self.permission_classes = [IsAuthenticated, CanDeleteRecords]
        self.check_permissions(request)
        candidate = self.get_object(pk)
        if candidate.resume and os.path.isfile(candidate.resume.path):
            os.remove(candidate.resume.path)
        log_action(request.user, 'DELETE', 'Candidate', candidate.id, f"Deleted candidate {candidate.name}")
        candidate.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RerankCandidatesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        job = get_object_or_404(JobPosting, pk=job_id)
        candidates = job.candidates.all()
        count = 0
        for candidate in candidates:
            if not candidate.anonymized_text:
                raw = extract_text(candidate.resume.path)
                anon = anonymize_text(raw) if raw else ''
                candidate.anonymized_text = anon
                candidate.save()
            if candidate.anonymized_text.strip():
                result = grade_resume(job.description, candidate.anonymized_text)
                if result and 'score' in result:
                    candidate.llm_score = float(result['score'])
                    candidate.llm_justification = result.get('justification', '')
                else:
                    candidate.llm_score = 0.0
                candidate.save()
                count += 1
        return Response({'message': f'Re‑ranked {count} candidates.'})  