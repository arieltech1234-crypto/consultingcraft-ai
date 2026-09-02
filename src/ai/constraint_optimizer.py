import logging

from groq import Groq
import re
from .groq_chat import chat_completion_text

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"


def _clamp_to_width(bullet: str, max_chars: int) -> str:
    """Trim an over-long bullet to fit one printed line, cutting at the
    cleanest available boundary.

    Prefers dropping a whole trailing clause (the text after the last comma
    or semicolon) so the result still reads as a complete thought; falls
    back to a whole-word trim when that would cut away too much. Only ever
    removes text -- never rewrites it -- so no facts can be altered here.
    """
    text = bullet.strip()
    if len(text) <= max_chars:
        return text

    head = text[:max_chars]
    for separator in (";", ","):
        cut = head.rfind(separator)
        # Only accept a clause cut that keeps most of the line; otherwise a
        # bullet with an early comma would lose nearly all its content.
        if cut >= int(max_chars * 0.6):
            return head[:cut].rstrip(" ,;:-") + "."

    cut = head.rfind(" ")
    trimmed = (head[:cut] if cut > 0 else head).rstrip(" ,;:-")
    return trimmed + "."


class ConstraintOptimizer:
    def __init__(self, api_key: str, model_name: str = "llama-3.1-8b-instant", max_iterations=3):
        self.client = Groq(api_key=api_key) if api_key else None
        self.max_iterations = max_iterations; self.model_name = model_name

    def optimize_batch(self, bullets: list, target_min_words: int, target_max_words: int) -> list:
        """
        Takes a list of already-drafted bullets and checks them all.
        Only sends failing bullets back to the LLM in a SINGLE batch call.
        """
        if not self.client:
            return bullets
            
        current_bullets = list(bullets)
        
        for iteration in range(self.max_iterations):
            failing = []
            for i, bullet in enumerate(current_bullets):
                wc = len(bullet.split())
                if wc < target_min_words or wc > target_max_words:
                    failing.append((i, bullet, wc))
            
            if not failing:
                print(f"All bullets passed constraint check on iteration {iteration + 1}!")
                return current_bullets
            
            print(f"Iteration {iteration + 1}: {len(failing)} bullets out of constraint. Fixing...")
            
            fix_items = "\n".join([
                f"{idx+1}. [{wc} words, need {target_min_words}-{target_max_words}] {bullet}"
                for idx, (i, bullet, wc) in enumerate(failing)
            ])
            
            prompt = f"""
Rewrite ONLY the following resume bullets so each is between {target_min_words} and {target_max_words} words,
aiming for {target_max_words} -- close to the top of that range, not just anywhere inside it (these lines are
printed at a fixed width, and a noticeably shorter bullet next to fuller ones leaves an obvious gap).
If a bullet is too short, expand it with more real detail (context, scope, method) using short plain words, not longer/rarer synonyms for words already there -- adding words should add content, not just eat more of the same line for the same idea. DO NOT invent or hallucinate new facts or metrics.
If a bullet is too long, condense without losing impact.
Keep the RAC format and strong action verbs. Output plain text only, one bullet per line, no numbering.

{fix_items}

Output exactly {len(failing)} rewritten lines:
"""
            try:
                response = self._call_with_retry(prompt)
                fixed_lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
                
                for j, (orig_idx, _, _) in enumerate(failing):
                    if j < len(fixed_lines):
                        clean = re.sub(r'^\d+[\.\)]\s*', '', fixed_lines[j]).strip('- *•').strip()
                        current_bullets[orig_idx] = clean
            except Exception as e:
                logger.warning("ConstraintOptimizer batch failed, keeping bullets as-is: %s", e)
                break
                
        return current_bullets

    def optimize_for_width(self, bullets: list, min_chars: int, max_chars: int) -> list:
        """Adjust each bullet so its rendered CHARACTER length lands close
        to max_chars (fills the printed line near the right margin) without
        exceeding it (which would wrap to a second line).

        Word count is only an approximation of how far a line reaches the
        margin -- word length varies a lot ("led" vs. "orchestrated") -- so
        this targets the actual thing that matters, and gives the model the
        bullet's precise current length so it can add or trim a real,
        measured amount rather than guess at a word-count proxy.
        """
        if not self.client:
            return bullets

        current_bullets = list(bullets)

        for iteration in range(self.max_iterations):
            failing = []
            for i, bullet in enumerate(current_bullets):
                length = len(bullet)
                if length < min_chars or length > max_chars:
                    failing.append((i, bullet, length))

            if not failing:
                logger.info("All bullets fit the target character width on iteration %d.", iteration + 1)
                return current_bullets

            logger.info("Iteration %d: %d bullet(s) outside the %d-%d character width. Fixing...",
                        iteration + 1, len(failing), min_chars, max_chars)

            fix_items = "\n".join([
                f"{idx+1}. [{length} characters, need {min_chars}-{max_chars}] {bullet}"
                for idx, (i, bullet, length) in enumerate(failing)
            ])

            prompt = f"""
Rewrite ONLY the following resume bullets so each is between {min_chars} and {max_chars} CHARACTERS long
(count every letter, space, and punctuation mark) -- as close to {max_chars} as possible without exceeding it.
The character count of each bullet is shown so you know exactly how much to add or remove.
If a bullet is too short, add real detail (specific scope, method, or numeric context already implied) using
plain words -- do not just substitute longer/rarer synonyms for words already there. DO NOT invent or
hallucinate new facts or metrics.
If a bullet is too long, condense without losing impact.
Keep the RAC format and strong action verbs. Output plain text only, one bullet per line, no numbering.

{fix_items}

Output exactly {len(failing)} rewritten lines:
"""
            try:
                response = self._call_with_retry(prompt)
                fixed_lines = [line.strip() for line in response.strip().split('\n') if line.strip()]

                for j, (orig_idx, _, _) in enumerate(failing):
                    if j < len(fixed_lines):
                        clean = re.sub(r'^\d+[\.\)]\s*', '', fixed_lines[j]).strip('- *•').strip()
                        current_bullets[orig_idx] = clean
            except Exception as e:
                logger.warning("ConstraintOptimizer width pass failed, keeping bullets as-is: %s", e)
                break

        # Deterministic last resort. The model is unreliable at hitting an
        # exact character count, and a bullet left over the ceiling wraps to
        # a second line -- the one thing this pass exists to prevent. Only
        # over-length bullets are touched; an under-length one just leaves a
        # gap at the margin, which is cosmetic and not worth mangling text
        # for.
        return [
            _clamp_to_width(bullet, max_chars) if len(bullet) > max_chars else bullet
            for bullet in current_bullets
        ]

    def optimize_for_length(self, drafter_agent, raw_experience: str, tone_rules: dict, target_min_words: int, target_max_words: int) -> str:
        """Single bullet optimization - kept for backward compatibility."""
        bullet = drafter_agent.draft_bullet(raw_experience, tone_rules)
        result = self.optimize_batch([bullet], target_min_words, target_max_words)
        return result[0]

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
