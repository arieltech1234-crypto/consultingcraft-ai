import logging

from groq import Groq
import re
from .groq_chat import chat_completion_text

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"

# Max bullets per LLM call to stay under token limits
CHUNK_SIZE = 5

# Currency markers used to catch a specific, observed fabrication mode: a
# small model mirroring a dollar-heavy reference resume's style by inventing
# a currency figure on a raw point that never had one (e.g. a music or sports
# achievement gaining a fabricated "$200M" of "brand value"). If a drafted
# bullet contains one of these that isn't in the raw point it was drafted
# from, the draft is discarded in favor of the untouched raw evidence.
_CURRENCY_MARKERS = ("$", "₹", "£", "€", "usd", "inr", "gbp", "eur", "rs.", " rs ")


def _has_fabricated_currency(raw: str, drafted: str) -> bool:
    raw_lower = raw.lower()
    drafted_lower = drafted.lower()
    return any(marker in drafted_lower and marker not in raw_lower for marker in _CURRENCY_MARKERS)

class BulletDrafter:
    def __init__(self, api_key: str, model_name: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key) if api_key else None; self.model_name = model_name
        
    def draft_bullets_batch(self, raw_experiences: list, tone_rules: dict, min_words: int, max_words: int, section_context: str = "") -> list:
        """
        Drafts bullets in chunked batch calls to stay under token limits.
        """
        if not self.client:
            return ["Mock bullet for: " + exp[:50] for exp in raw_experiences]
        
        # Chunk raw experiences to avoid token limit
        all_drafted = []
        for i in range(0, len(raw_experiences), CHUNK_SIZE):
            chunk = raw_experiences[i:i + CHUNK_SIZE]
            drafted = self._draft_chunk(chunk, tone_rules, min_words, max_words, section_context)
            all_drafted.extend(drafted)
        
        return all_drafted
    
    def _draft_chunk(self, raw_chunk: list, tone_rules: dict, min_words: int, max_words: int, section_context: str = "") -> list:
        """Drafts a small chunk of bullets in one API call."""
        # Never truncate the source evidence: it is the factual grounding the
        # model must rewrite from. Cutting it mid-sentence (as a fixed [:150]
        # slice previously did) hides the back half of any evidence line over
        # 150 chars -- commonly exactly where a dollar amount or closing
        # clause lives -- and the model fabricates a plausible-looking ending
        # instead. CHUNK_SIZE keeps each call to a handful of full lines.
        numbered_list = "\n".join([f"{i+1}. {exp}" for i, exp in enumerate(raw_chunk)])
        
        section_line = f"Section: {section_context}. " if section_context else ""
        
        # Build compact reference context
        verb_line = "Verbs: Spearheaded, Orchestrated, Optimized, Synthesized, Drove"
        example_line = ""
        style_line = ""
        jd_line = ""

        if tone_rules:
            verbs = tone_rules.get("all_recommended_verbs", tone_rules.get("extracted_verbs", []))
            if verbs:
                verb_line = f"Verbs: {', '.join(verbs[:10])}"

            examples = tone_rules.get("example_bullets", [])
            if examples:
                example_line = f"\nStyle examples from reference CV:\n" + "\n".join([f"- {b[:120]}" for b in examples[:3]])

            structure = tone_rules.get("structure_pattern", "")
            tone = tone_rules.get("tone_analysis", "")
            if structure or tone:
                style_line = f"\nStyle: {structure[:100]} {tone[:100]}"

            jd_keywords = tone_rules.get("jd_keywords", [])
            if jd_keywords:
                jd_line = (
                    f"\nTarget-role keywords to mirror ONLY where truthfully supported by "
                    f"the raw point (never fabricate a skill or tool): {', '.join(jd_keywords[:10])}"
                )

        prompt = f"""Rewrite these resume bullets in RAC format (Result-Action-Context).
{section_line}{verb_line}
Rules: {min_words}-{max_words} words each -- aim for {max_words}, close to the top of that range, not just anywhere inside it (these lines are printed at a fixed width, and a noticeably shorter bullet next to fuller ones leaves an obvious gap). Never go below {min_words} or above {max_words}.
Favor short, plain phrasing over long hyphenated compounds or stacked qualifiers (e.g. "cross-team" not "cross-functional-and-interdepartmental") so this word count fills the printed line with real content, rather than a handful of long words eating the same space. Plain text only, one per line, no numbering.
CRITICAL: Every number, percentage, and currency figure in your output must already appear in the matching raw point below. Never invent, estimate, or carry over a number/currency figure from the style examples or from another raw point. If a raw point has no metric, do not add one.
If a raw point lists the same figure in multiple currencies (e.g. "GBP 100K / USD 133K / INR 1.28Cr"), pick exactly ONE currency and drop the rest -- prefer USD for international corporate/client figures and the candidate's local currency for personal figures (student portfolios, local clubs, local fundraising).{style_line}{example_line}{jd_line}

Raw points:
{numbered_list}

Output {len(raw_chunk)} lines:"""

        try:
            response = self._call_with_retry(prompt)
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            cleaned = []
            for line in lines:
                line = re.sub(r'^\d+[\.\)]\s*', '', line)
                line = line.strip('- *•·')
                if line:
                    cleaned.append(line.strip())

            # Preserve a one-to-one mapping even if the model returns too few lines.
            cleaned = cleaned[:len(raw_chunk)]
            if len(cleaned) < len(raw_chunk):
                cleaned.extend(raw_chunk[len(cleaned):])

            # Safety net: revert to the untouched raw evidence for any bullet
            # where the model injected a currency figure not present in the
            # source line, rather than shipping a fabricated dollar amount.
            for i in range(len(cleaned)):
                if i < len(raw_chunk) and _has_fabricated_currency(raw_chunk[i], cleaned[i]):
                    cleaned[i] = raw_chunk[i]
            return cleaned
        except Exception as e:
            # Never surface an error message as if it were bullet content --
            # confirmed this happened for real: a transient connection error
            # produced a literal "Failed to draft bullet. Error: ..." string
            # that was then fed into the optimizer as "content" to shorten,
            # which the model correctly refused to do, and THAT refusal text
            # ALSO ended up in the final resume. Falling back to the
            # untouched raw evidence is always safe, sensible content.
            logger.warning("BulletDrafter chunk failed, keeping raw evidence: %s", e)
            return list(raw_chunk)

    def draft_bullet(self, raw_experience: str, tone_rules: dict) -> str:
        """Single bullet drafting - kept for backward compatibility."""
        results = self.draft_bullets_batch([raw_experience], tone_rules, 16, 24)
        return results[0]

    def _call_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Calls Groq API with automatic retry on rate limit errors."""
        return chat_completion_text(
            self.client,
            self.model_name,
            prompt,
            temperature=0.7,
            max_tokens=1500,
            max_retries=max_retries,
        )
