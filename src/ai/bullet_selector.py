import logging

import instructor
from groq import Groq

from .schema import Section

logger = logging.getLogger(__name__)


def _trim_to_count(section: Section, target_count: int) -> None:
    """Deterministically cut a section down to exactly target_count bullets,
    in place, keeping earlier entries/groups intact before later ones."""
    remaining = target_count
    for entry in section.entries:
        for group in entry.groups:
            if remaining <= 0:
                group.bullets = []
            elif len(group.bullets) > remaining:
                group.bullets = group.bullets[:remaining]
                remaining = 0
            else:
                remaining -= len(group.bullets)


class BulletSelector:
    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile"):
        raw_client = Groq(api_key=api_key) if api_key else None
        self.client = instructor.from_groq(raw_client, mode=instructor.Mode.JSON) if raw_client else None
        self.model_name = model_name

    def select_best_lines(self, section: Section, target_count: int, target_themes: list[str] | None = None) -> Section:
        """
        Takes a hierarchical Section and prunes bullets to meet the target_count.
        Maintains the structure (entries, groups). When target_themes is given
        (e.g. from job-description analysis), bullets matching those themes are
        favored so the selection is tailored, not just generically "impactful".
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

        relevance_rule = ""
        if target_themes:
            relevance_rule = (
                f"3b. Prioritize bullets relevant to these target-role themes: "
                f"{', '.join(target_themes)}.\n"
            )

        prompt = f"""You are a ruthless BCG recruiter editing a resume.
We must cut the following section down to exactly {target_count} bullets total across all entries.
Currently it has {current_count} bullets.

RULES:
1. Preserve the exact structure (entries, headers, groups).
2. DO NOT rewrite the bullets, just select the best ones.
3. Keep the most impactful, quantified, and relevant bullets -- bullets describing what the
   CANDIDATE personally did, decided, or delivered.
{relevance_rule}4. Drop weak, vague, or overly technical bullets, and drop bullets that only describe the
   employer/company/context (size, founding year, service lines, market description) rather
   than something the candidate did.
5. You MUST return exactly {target_count} bullets in total.

SECTION JSON:
{section.model_dump_json()}
"""

        try:
            result = self.client.chat.completions.create(
                model=self.model_name,
                response_model=Section,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2500,
            )
        except Exception as e:
            logger.warning("BulletSelector failed for section '%s': %s", section.section_name, e)
            return section

        result_count = sum(len(group.bullets) for entry in result.entries for group in entry.groups)
        if result_count > target_count:
            # "Return exactly N" on a nested JSON schema is a request, not a
            # guarantee -- models (even at temperature 0) routinely keep more
            # bullets than asked. The page-fit budget this count is meant to
            # enforce is a hard constraint, so it's enforced here in code
            # rather than trusted to the model.
            logger.warning(
                "BulletSelector for '%s' returned %d bullets, wanted %d; trimming.",
                section.section_name, result_count, target_count,
            )
            _trim_to_count(result, target_count)
        return result
