import json
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

def _truncate(text, max_chars=2000):
    """Limit resume text to avoid context window overflow."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"

def grade_resume(job_description, anonymized_resume):
    """
    Send anonymized resume and job description to DeepSeek.
    Returns a dict with 'score' and 'justification', or None on failure.
    """
    anon_short = anonymized_resume   

    prompt = f"""You are an experienced HR professional evaluating a candidate. Read the anonymized resume below and compare it to the job description.

Rate the candidate on a scale of 0–100 using this rubric:
- Relevant skills (40 points)
- Years of relevant experience (30 points)
- Certifications and additional qualifications (30 points)

Write your evaluation as a JSON object with two fields:
- "score": a number between 0 and 100
- "justification": a natural, conversational explanation of the score, exactly 3 sentences. Write like a human HR professional talking to a colleague. Use the "sandwich method": start with a strength, then mention a gap or area for growth (which can include missing certifications if applicable), and end with a positive overall impression. Do NOT mention specific years of experience, educational background, school name, or degree.

Example:
{{
  "score": 74,
  "justification": "The candidate's hands‑on skills align well with the core requirements, and they hold an AWS certification that adds value to the team. They haven't yet worked with one of our preferred tools, which could slow their initial ramp‑up. Overall, their practical experience and relevant certification make them a promising fit for the role."
}}

Job Description:
{job_description}

Resume (anonymized):
{anon_short}"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are an HR assistant that returns only valid JSON. Carefully review the resume for certifications and mention them if they add value. Write justifications using the sandwich method."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,        
            max_tokens=600            
        )
        content = response.choices[0].message.content.strip()

        # Clean markdown fences if present
        if content.startswith("```"):
            content = content.strip("```").strip()
            if content.startswith("json"):
                content = content[4:].strip()

        result = json.loads(content)
        return result

    except Exception as e:
        logger.exception("DeepSeek API call failed")
        return None