"""Extract section names from an optional DOCX structure reference."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


class TemplateParser:
    def parse(self, template_path: str) -> list[str]:
        path = Path(template_path)
        return self.parse_bytes(path.read_bytes(), path.name)

    def parse_bytes(self, content: bytes, filename: str = "template.docx") -> list[str]:
        if Path(filename).suffix.lower() != ".docx":
            raise ValueError("The structure reference must be a DOCX file.")

        import docx
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        document = docx.Document(BytesIO(content))
        sections: list[str] = []
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text or paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER:
                continue
            is_bold = any(run.bold for run in paragraph.runs if run.text.strip())
            is_upper = text == text.upper() and len(text) > 2
            is_short = len(text.split()) <= 6 and not text.startswith("[")
            if is_bold and (is_upper or is_short):
                normalized = text.title() if is_upper else text
                if normalized not in sections:
                    sections.append(normalized)

        return sections or self.default_sections()

    @staticmethod
    def default_sections() -> list[str]:
        return [
            "Education",
            "AI product experience",
            "Leadership & extracurriculars",
            "Skills & interests",
        ]

    # Backwards-compatible alias for older callers.
    def _default_sections(self) -> list[str]:
        return self.default_sections()
