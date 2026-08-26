"""
ReferenceAnalyzer: Deep analysis of reference CVs.
Extracts action verbs actually used, identifies example bullet patterns,
finds similar experiences, and analyzes how they were structured.
"""
from groq import Groq
import json
import re
from .groq_chat import chat_completion

# Harvard Business School recommended action verbs for consulting resumes
HARVARD_ACTION_VERBS = [
    # Leadership & Management
    "Spearheaded", "Orchestrated", "Directed", "Championed", "Mobilized",
    "Galvanized", "Steered", "Oversaw", "Instituted", "Pioneered",
    # Analysis & Strategy
    "Synthesized", "Diagnosed", "Evaluated", "Quantified", "Modeled",
    "Benchmarked", "Assessed", "Mapped", "Dissected", "Triangulated",
    # Impact & Results
    "Drove", "Accelerated", "Captured", "Delivered", "Generated",
    "Unlocked", "Realized", "Yielded", "Amplified", "Maximized",
    # Execution & Operations
    "Optimized", "Streamlined", "Restructured", "Automated", "Consolidated",
    "Transformed", "Redesigned", "Implemented", "Deployed", "Scaled",
    # Communication & Influence
    "Advised", "Presented", "Negotiated", "Influenced", "Facilitated",
    "Articulated", "Aligned", "Counseled", "Persuaded", "Engaged",
]


class ReferenceAnalyzer:
    def __init__(self, api_key: str, model_name: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key) if api_key else None
        self.model_name = model_name

    def analyze(self, ref_text: str, master_cv_text: str = "") -> dict:
        """
        Deep analysis of reference CVs. Returns a rich dict with:
        - extracted_verbs: actual action verbs found in the reference CVs
        - harvard_verbs: curated Harvard action verb list
        - example_bullets: 5-8 best example bullets from the reference CVs
        - structure_patterns: how the reference structures their bullets
        - tone_analysis: detailed tone description
        - similar_experiences: if master CV context given, finds analogous experiences
        """
        if not self.client:
            return self._default_patterns()

        try:
            response = chat_completion(
                self.client,
                self.model_name,
                messages=[
                    {"role": "system", "content": """You are an elite MBB career coach doing a DEEP analysis of reference CVs.

Your job is to extract SPECIFIC, ACTIONABLE patterns that will be used to rewrite another person's resume.

Return a JSON object with these keys:
1. "extracted_verbs": List of 10-15 strong action verbs ACTUALLY USED in the reference text. Pick the best ones.
2. "example_bullets": List of 5-8 of the BEST bullet points from the reference CV. Copy them exactly as written. These will be shown as examples to the bullet drafter.
3. "structure_pattern": A string describing HOW the reference structures their bullets. Be specific. E.g. "Starts with a quantified result (percentage or dollar amount), followed by the action taken, ending with the business context. Uses semicolons to separate sub-achievements."
4. "tone_analysis": A string describing the TONE. E.g. "Confident, metrics-heavy, uses superlatives like 'first-ever' and 'largest'. Avoids passive voice entirely. Every bullet has at least one number."
5. "key_themes": List of 3-5 themes or skill areas the reference emphasizes (e.g. "data-driven decision making", "cross-functional leadership", "client relationship management")

Be extremely specific. Do not give generic advice. Extract patterns from THIS specific reference text."""},
                    {"role": "user", "content": f"Analyze this reference CV deeply:\n\n{ref_text[:4000]}"}
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            text = response.choices[0].message.content
            print(f"DEBUG ReferenceAnalyzer response: {text[:300]}")

            try:
                patterns = json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    patterns = json.loads(match.group())
                else:
                    patterns = {}

            # Enrich with Harvard verbs
            patterns["harvard_verbs"] = HARVARD_ACTION_VERBS
            
            # Merge extracted verbs with Harvard verbs for the drafter
            extracted = patterns.get("extracted_verbs", [])
            patterns["all_recommended_verbs"] = list(set(extracted + HARVARD_ACTION_VERBS[:15]))

            return patterns

        except Exception as e:
            print(f"Error in analyze: {e}")
            return self._default_patterns()

    def _default_patterns(self) -> dict:
        return {
            "extracted_verbs": [],
            "harvard_verbs": HARVARD_ACTION_VERBS,
            "all_recommended_verbs": HARVARD_ACTION_VERBS[:15],
            "example_bullets": [],
            "structure_pattern": "Result-Action-Context (RAC): Lead with a quantified result, describe the action taken, provide business context.",
            "tone_analysis": "Quantitative, outcome-oriented, active voice. Every bullet should contain at least one metric.",
            "key_themes": ["analytical problem solving", "leadership", "client delivery"],
        }
