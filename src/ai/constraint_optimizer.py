from groq import Groq
import re
from .groq_chat import chat_completion

MODEL = "llama-3.1-8b-instant"

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
Rewrite ONLY the following resume bullets so each is EXACTLY between {target_min_words} and {target_max_words} words.
If a bullet is too short, expand it by using more descriptive professional language, but DO NOT invent or hallucinate new facts or metrics.
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
                print(f"Optimization error: {e}")
                break
                
        return current_bullets

    def optimize_for_length(self, drafter_agent, raw_experience: str, tone_rules: dict, target_min_words: int, target_max_words: int) -> str:
        """Single bullet optimization - kept for backward compatibility."""
        bullet = drafter_agent.draft_bullet(raw_experience, tone_rules)
        result = self.optimize_batch([bullet], target_min_words, target_max_words)
        return result[0]

    def _call_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Calls Groq API with automatic retry on rate limit errors."""
        response = chat_completion(
            self.client,
            self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
            max_retries=max_retries,
        )
        return response.choices[0].message.content
