import logging
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from PyPDF2 import PdfReader
from docx import Document

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ''
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + '\n'
    return text


def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return '\n'.join([p.text for p in doc.paragraphs])


def extract_text(file_path):
    """Detect file type and return raw text."""
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    else:
        return ''


def compute_matching_keywords(job_desc, required_skills_str, resume_text, top_n=10):
    """
    Returns:
        score: float 0‑1 (cosine similarity)
        matching_keywords: dict with:
            - matched_skills: list of required skills found in resume
            - missing_skills: list of required skills not found
            - top_contributing_terms: list of (term, contribution) tuples
    """
    # Combine both documents
    documents = [job_desc, resume_text]
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(documents)

    # Cosine similarity between job description (row 0) and resume (row 1)
    score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    score = round(float(score), 4)

    # Extract top contributing terms
    feature_names = vectorizer.get_feature_names_out()
    job_weights = tfidf_matrix[0].toarray().flatten()
    resume_weights = tfidf_matrix[1].toarray().flatten()
    contributions = job_weights * resume_weights
    top_indices = contributions.argsort()[-top_n:][::-1]
    top_terms = []
    for idx in top_indices:
        if contributions[idx] > 0:
            top_terms.append((feature_names[idx], round(float(contributions[idx]), 4)))

    # Check required skills
    required_skills = [s.strip().lower() for s in required_skills_str.split(',') if s.strip()]
    resume_lower = resume_text.lower()
    matched = []
    missing = []
    for skill in required_skills:
        if skill in resume_lower:
            matched.append(skill)
        else:
            missing.append(skill)

    matching_keywords = {
        'matched_skills': matched,
        'missing_skills': missing,
        'top_contributing_terms': top_terms
    }
    return score, matching_keywords