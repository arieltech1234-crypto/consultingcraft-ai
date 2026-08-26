import instructor
from groq import Groq
from .schema import Section

class BulletSelector:
    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile"):
        raw_client = Groq(api_key=api_key) if api_key else None
        self.client = instructor.from_groq(raw_client, mode=instructor.Mode.JSON) if raw_client else None
        self.model_name = model_name

    def select_best_lines(self, section: Section, target_count: int) -> Section:
        """
        Takes a hierarchical Section and prunes bullets to meet the target_count.
        Maintains the structure (entries, groups).
        """
        if not self.client:
            return section
            
        current_count = sum(
            len(group.bullets)
            for entry in section.entries
            for group in entry.groups
        )
        if current_count <= target_count:
            return section

        prompt = f"""You are a ruthless BCG recruiter editing a resume.
We must cut the following section down to exactly {target_count} bullets total across all entries.
Currently it has {current_count} bullets.

RULES:
1. Preserve the exact structure (entries, headers, groups).
2. DO NOT rewrite the bullets, just select the best ones.
3. Keep the most impactful, quantified, and relevant bullets.
4. Drop weak, vague, or overly technical bullets.
5. You MUST return exactly {target_count} bullets in total.

SECTION JSON:
{section.model_dump_json()}
"""

        try:
            return self.client.chat.completions.create(
                model=self.model_name,
                response_model=Section,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2500,
            )
        except Exception as e:
            import streamlit as st
            st.error(f"BulletSelector Exception: {e}")
            print(f"BulletSelector error: {e}")
            return section

