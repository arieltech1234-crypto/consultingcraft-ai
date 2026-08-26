"""Deterministic A4 DOCX generation for the portfolio demo."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


class CVGenerator:
    """Generate a compact, recruiter-readable CV without shared temp files."""

    def generate_docx_bytes(
        self,
        structured_data: dict,
        layout_preferences: dict | None = None,
        template_bytes: bytes | None = None,
    ) -> bytes:
        from docxtpl import DocxTemplate

        if template_bytes:
            buffer = BytesIO(template_bytes)
            doc = DocxTemplate(buffer)
        else:
            default_path = Path("src/demo_assets/default_template.docx")
            if not default_path.exists():
                raise FileNotFoundError("Default template not found. Please upload a visual template.")
            doc = DocxTemplate(str(default_path))

        # Re-structure context to simply pass the sections down
        # so templates can loop over `sections`, then `entries`, then `groups`
        context = {
            "name": structured_data.get("name") or "Candidate Name",
            "contact_line": structured_data.get("contact_line", "").strip(),
            "sections": structured_data.get("resume_schema", {}).get("sections", [])
        }

        doc.render(context)
        out_buffer = BytesIO()
        doc.save(out_buffer)
        return out_buffer.getvalue()

    def generate_docx(
        self, structured_data: dict, layout_preferences: dict, output_path: str, template_bytes: bytes | None = None
    ) -> bool:
        """Backwards-compatible file writer used by scripts and tests."""
        content = self.generate_docx_bytes(structured_data, layout_preferences, template_bytes)
        Path(output_path).write_bytes(content)
        return True
