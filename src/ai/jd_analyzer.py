"""Distinguish job descriptions from shortlisted reference resumes, and
extract job-description requirements to drive relevance/alignment instead
of only writing style."""

from __future__ import annotations

import json
import logging
import re

from groq import Groq

from .groq_chat import chat_completion_text

logger = logging.getLogger(__name__)

_JD_SIGNALS = (
    "responsibilities", "requirements", "qualifications", "we are looking for",
    "job description", "about the role", "about you", "what you'll do",
    "what you will do", "who you are", "role overview", "minimum qualifications",
    "preferred qualifications", "job type", "equal opportunity employer",
    "reports to", "years of experience required",
)
_RESUME_SIGNALS = (
    "education", "work experience", "professional experience", "certifications",
    "gpa", "linkedin.com/in", "objective", "extracurricular", "references available",
)
_DATE_RANGE_RE = re.compile(r"(19|20)\d{2}\s*[-–]\s*((19|20)\d{2}|present)")


def classify_reference_text(text: str) -> str:
    """Heuristic classification of an uploaded reference file's text.

    Returns "jd" for a job description, "resume" for a reference/shortlisted
    resume. Deterministic and free (no API call) since it just decides which
    downstream analyzer to route the text to.
    """
    lowered = text.lower()
    jd_score = sum(1 for signal in _JD_SIGNALS if signal in lowered)
    resume_score = sum(1 for signal in _RESUME_SIGNALS if signal in lowered)
    resume_score += min(len(_DATE_RANGE_RE.findall(lowered)), 3)
    return "jd" if jd_score > resume_score else "resume"


class JDAnalyzer:
    """Extracts what a job description actually requires, for alignment
    (relevance and keyword coverage) rather than writing-style modeling."""

    def __init__(self, api_key: str, model_name: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key) if api_key else None
        self.model_name = model_name

    def analyze(self, jd_text: str) -> dict:
        if not self.client or not jd_text.strip():
            return self._default()

        try:
            response_text = chat_completion_text(
                self.client,
                self.model_name,
                f"""You are analyzing a job description to determine what a candidate's
resume should emphasize to be well-aligned with this specific role.

Return ONLY a JSON object with these keys:
1. "required_skills": 8-12 concrete skills, tools, or competencies explicitly required or strongly implied.
2. "keywords": 10-15 short exact keywords or phrases from the posting worth mirroring in resume language.
3. "responsibilities": 4-6 core responsibilities described in the posting.
4. "seniority": one short phrase describing the level implied (e.g. "entry-level analyst", "senior PM").

Be specific to THIS posting; do not give generic career advice.

JOB DESCRIPTION:
{jd_text[:4000]}""",
                temperature=0.2,
                max_tokens=800,
            )
            try:
                requirements = json.loads(response_text)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", response_text, re.DOTALL)
                requirements = json.loads(match.group()) if match else {}

            return {
                "required_skills": requirements.get("required_skills", []) or [],
                "keywords": requirements.get("keywords", []) or [],
                "responsibilities": requirements.get("responsibilities", []) or [],
                "seniority": requirements.get("seniority", "") or "",
            }
        except Exception as e:
            logger.warning("JDAnalyzer failed, returning empty requirements: %s", e)
            return self._default()

    @staticmethod
    def _default() -> dict:
        return {"required_skills": [], "keywords": [], "responsibilities": [], "seniority": ""}


def compute_jd_coverage(schema_dict: dict, jd_requirements: dict) -> dict:
    """Checks which JD required_skills/keywords already appear somewhere in the
    drafted bullets, so a human reviewer can see gaps before export."""
    terms = list(dict.fromkeys(
        (jd_requirements.get("required_skills") or [])
        + (jd_requirements.get("keywords") or [])
    ))
    if not terms:
        return {"covered": [], "missing": [], "total": 0}

    all_text = " ".join(
        str(bullet)
        for section in schema_dict.get("sections", [])
        for entry in section.get("entries", [])
        for group in entry.get("groups", [])
        for bullet in group.get("bullets", [])
    ).lower()

    covered = [term for term in terms if term.lower() in all_text]
    missing = [term for term in terms if term.lower() not in all_text]
    return {"covered": covered, "missing": missing, "total": len(terms)}
