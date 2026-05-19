import requests
import json
import logging
from django.conf import settings
import json_repair

logger = logging.getLogger(__name__)

def _call_openrouter_api(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int, json_mode: bool = False) -> str:
    """Helper to communicate with OpenRouter API."""
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120 if max_tokens > 1000 else 30,
    )
    
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def analyze_candidate_for_job(job_description: str, resume_text: str, strictness: int = 80) -> dict:
    """
    Call OpenRouter LLM to analyze a candidate's resume against a job description.
    Returns structured scoring data.
    """
    
    system_prompt = """You are an expert AI recruiter analyzing resumes against job descriptions.
    Evaluate the candidate thoroughly and return a JSON object with these exact fields:
    
    {
        "overall_score": <int 0-100>,
        "skills_score": <int 0-100>,
        "experience_score": <int 0-100>,
        "culture_score": <int 0-100>,
        "resume_score": <int 0-100>,
        "matched_skills": ["skill1", "skill2", ...],
        "missing_skills": ["skill1", "skill2", ...],
        "strengths": ["strength1", "strength2", ...],
        "gaps": ["gap1", "gap2", ...],
        "recommendation": "Strong Hire" | "Hire" | "Review" | "Reject",
        "experience_years": <int>,
        "culture_fit": "High" | "Medium" | "Low",
        "summary": "2-3 sentence assessment"
    }
    
    Scoring criteria (strictness level: {strictness}/100):
    - Higher strictness = more exacting requirements matching
    - skills_score: How well candidate's skills match required skills
    - experience_score: Relevance and depth of experience
    - culture_score: Inferred cultural fit based on resume signals
    - resume_score: Quality, clarity, and professionalism of resume
    - overall_score: Weighted average of all dimensions
    
    Return ONLY valid JSON, no markdown formatting blocks like ```json, just the raw JSON object."""
    
    user_prompt = f"""
    === JOB DESCRIPTION ===
    {job_description}
    
    === CANDIDATE RESUME ===
    {resume_text}
    
    Analyze this candidate for the above job. Strictness level: {strictness}/100.
    Return the JSON scoring object."""
    
    try:
        content = _call_openrouter_api(
            system_prompt=system_prompt.replace("{strictness}", str(strictness)),
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4000,
            json_mode=True
        )
        
        parsed_data = json_repair.loads(content)
        if isinstance(parsed_data, str):
            # If json_repair completely fails, it returns the string
            raise ValueError(f"Failed to decode JSON from OpenRouter response. Raw: {content[:200]}")
            
        return parsed_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter API request failed: {e}")
        raise
    except ValueError as e:
        logger.error(str(e))
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ai_analyzer: {e}")
        raise

def extract_job_requirements(job_description: str) -> str:
    """
    Extract core requirements from a job description to reduce token usage
    when analyzing candidates.
    """
    system_prompt = """You are an expert AI recruiter. Your task is to extract the core requirements from a job description.
    Return a concise, bulleted list covering ONLY:
    - Must-have skills and technologies
    - Required years of experience
    - Key responsibilities
    - Necessary education/certifications
    
    Keep it as brief as possible while retaining the critical requirements used to evaluate candidates. Do not include fluff."""
    
    user_prompt = f"=== JOB DESCRIPTION ===\n{job_description}"
    
    try:
        content = _call_openrouter_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=1000,
            json_mode=False
        )
        return content.strip()
    except Exception as e:
        logger.error(f"Failed to extract job requirements: {e}")
        return job_description  # Fallback to the full description
