"""
SectionMapper: Extracts a hierarchical resume schema from the raw Master CV text.
"""
import instructor
from groq import Groq
from .schema import ResumeSchema

class SectionMapper:
    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile"):
        raw_client = Groq(api_key=api_key) if api_key else None
        self.client = instructor.from_groq(raw_client, mode=instructor.Mode.JSON) if raw_client else None
        self.model_name = model_name

    def map_lines_to_sections(self, template_sections: list[str], raw_text: str, status=None) -> ResumeSchema:
        """
        Parses the entire master CV text into a structured hierarchical ResumeSchema.
        Processes in chunks to avoid output token limits and TPM rate limits.
        """
        if not self.client or not raw_text:
            return ResumeSchema(sections=[])

        lines = raw_text.split('\n')
        chunk_size = 40
        chunks = ['\n'.join(lines[i:i + chunk_size]) for i in range(0, len(lines), chunk_size)]
        
        merged_schema = ResumeSchema(sections=[])
        
        import time
        import streamlit as st
        
        for idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
                
            prompt = f"""You are an expert resume parser.
Extract the provided resume text chunk into a strict hierarchical format.

TARGET SECTIONS: {template_sections}

RULES:
1. Map the text to the closest Target Section name.
2. For each major entry, extract the left header (e.g., "Google | PM") and right header (e.g., "Aug 2021").
3. Extract any short italicized or summary descriptions below the header into the `summary` field.
4. DO NOT invent your own categories, groupings, or buckets! Keep all bullets together under a single Group with an empty `group_name` unless the original resume explicitly contains a literal sub-heading.
5. Do NOT summarize or change the bullet points. Extract them exactly as written.

RESUME TEXT CHUNK:
{chunk}
"""

            try:
                if status:
                    status.write(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ Mapping chunk {idx + 1} of {len(chunks)}...")
                # Add delay between chunks to avoid TPM limits
                if idx > 0:
                    time.sleep(4)
                    
                chunk_schema = self.client.chat.completions.create(
                    model=self.model_name,
                    response_model=ResumeSchema,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2500,
                )
                
                # Merge into the main schema
                for section in chunk_schema.sections:
                    # Find if this section already exists in merged_schema
                    existing_section = next((s for s in merged_schema.sections if s.section_name == section.section_name), None)
                    if existing_section:
                        existing_section.entries.extend(section.entries)
                    else:
                        merged_schema.sections.append(section)
                        
            except Exception as e:
                # If a chunk fails, log it and continue to the next chunk
                print(f"SectionMapper Extraction Error on chunk {idx}: {e}")
                
        return merged_schema

