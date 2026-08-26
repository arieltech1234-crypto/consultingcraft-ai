from groq import Groq
import json
import re
from .groq_chat import chat_completion

MODEL = "llama-3.1-8b-instant"

# Max bullets per LLM call to stay under token limits
CHUNK_SIZE = 5

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
        numbered_list = "\n".join([f"{i+1}. {exp[:150]}" for i, exp in enumerate(raw_chunk)])
        
        section_line = f"Section: {section_context}. " if section_context else ""
        
        # Build compact reference context
        verb_line = "Verbs: Spearheaded, Orchestrated, Optimized, Synthesized, Drove"
        example_line = ""
        style_line = ""
        
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
        
        prompt = f"""Rewrite these resume bullets in RAC format (Result-Action-Context).
{section_line}{verb_line}
Rules: {min_words}-{max_words} words each. No hallucinated facts/numbers. Plain text only, one per line, no numbering.{style_line}{example_line}

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
            return cleaned
        except Exception as e:
            return [f"Failed to draft bullet. Error: {str(e)}"] * len(raw_chunk)

    def draft_bullet(self, raw_experience: str, tone_rules: dict) -> str:
        """Single bullet drafting - kept for backward compatibility."""
        results = self.draft_bullets_batch([raw_experience], tone_rules, 16, 24)
        return results[0]

    def apply_mece_bucketing(self, drafted_bullets: list) -> dict:
        if not self.client:
            return {"Experience": drafted_bullets}
            
        prompt = f"""Organize these resume bullets into sections like "Education", "Work Experience", "Extracurriculars".
Return ONLY a JSON object where keys are section names and values are lists of bullet strings.

Bullets:
{json.dumps(drafted_bullets)}"""
        try:
            response = self._call_with_retry(prompt)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    return json.loads(match.group())
                return {"Experience": drafted_bullets}
        except Exception as e:
            return {"Experience": drafted_bullets}

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
