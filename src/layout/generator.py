"""Deterministic A4 DOCX generation for the portfolio demo."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape


def _escape_for_xml(value):
    """Recursively XML-escape string values in a docxtpl render context.

    docxtpl (0.16.8) does not auto-escape substituted text: a raw "&" in
    any field (a bullet mentioning "R&D", a section named "Leadership &
    Extracurriculars") is silently dropped rather than rendered, since it
    isn't valid inside the underlying XML's text nodes as-is. Escaping here
    is what makes the entity round-trip correctly instead of vanishing.
    """
    if isinstance(value, str):
        return _xml_escape(value)
    if isinstance(value, dict):
        return {key: _escape_for_xml(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_escape_for_xml(item) for item in value]
    return value


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
            repo_root = Path(__file__).resolve().parent.parent.parent
            default_path = repo_root / "data" / "templates" / "isb_jinja_template.docx"
            if not default_path.exists():
                raise FileNotFoundError("ISB template not found.")
            doc = DocxTemplate(str(default_path))

        sections = structured_data.get("resume_schema", {}).get("sections", [])
        # Section names are uppercased here, in Python, rather than via a
        # "|upper" Jinja filter in the template: the filter runs on values
        # AFTER _escape_for_xml below, which would turn e.g. "&amp;" into
        # the invalid entity "&AMP;" and silently drop the ampersand again.
        uppercased_sections = [
            {**section, "section_name": str(section.get("section_name", "")).upper()}
            for section in sections
        ]

        # Re-structure context to simply pass the sections down
        # so templates can loop over `sections`, then `entries`, then `groups`
        context = _escape_for_xml({
            "name": structured_data.get("name") or "Candidate Name",
            "contact_line": structured_data.get("contact_line", "").strip(),
            "sections": uppercased_sections,
        })

        doc.render(context)
        out_buffer = BytesIO()
        doc.save(out_buffer)
        content = out_buffer.getvalue()

        # The template only carries content structure; visual density (font
        # size, margins, line/section spacing) is applied here so the sliders
        # exposed in the UI actually affect the exported file instead of only
        # feeding the page-fit estimate.
        if layout_preferences:
            content = self._apply_layout(content, layout_preferences, sections)
        return content

    @staticmethod
    def _apply_layout(content: bytes, layout_preferences: dict, sections: list) -> bytes:
        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_LINE_SPACING

        font_size = float(layout_preferences.get("font_size", 10))
        side_margin = float(layout_preferences.get("side_margin_inches", 0.55))
        top_margin = float(layout_preferences.get("top_margin_inches", 0.5))
        bottom_margin = float(layout_preferences.get("bottom_margin_inches", top_margin))
        line_spacing_pt = float(layout_preferences.get("line_spacing_pt", font_size + 1))
        section_spacing_pt = float(layout_preferences.get("section_spacing_pt", 6))
        sub_section_spacing_pt = float(layout_preferences.get("sub_section_spacing_pt", 2.5))

        document = Document(BytesIO(content))

        for docx_section in document.sections:
            docx_section.left_margin = Inches(side_margin)
            docx_section.right_margin = Inches(side_margin)
            docx_section.top_margin = Inches(top_margin)
            docx_section.bottom_margin = Inches(bottom_margin)

        for style_name in ("Normal", "List Bullet"):
            try:
                style = document.styles[style_name]
            except KeyError:
                continue
            style.font.size = Pt(font_size)
            style.paragraph_format.space_before = Pt(0)
            style.paragraph_format.space_after = Pt(sub_section_spacing_pt)
            if style_name == "List Bullet":
                # Word's built-in "List Bullet" style indents text 1.25in
                # with a 0.25in hanging indent (bullet at 1in, text at
                # 1.25in) -- a huge gap at this font size. Matches the
                # reference resume's own tight ~0.1in bullet indent instead.
                style.paragraph_format.left_indent = Pt(7.1)
                style.paragraph_format.first_line_indent = Pt(-7.1)
            # "At least" (not "exactly"): this matches how the user's own
            # working reference resume is actually built -- a tiny minimum
            # that only sets a floor, letting Word use the font's real
            # required height. "Exactly" at a value below that genuinely
            # overlaps/garbles text once a full page of wrapped lines stacks
            # up (confirmed: it looked fine on a 3-line sample, but broke on
            # real content -- an "exactly" value must never go below what
            # the font needs, whereas "at least" can't ever go wrong).
            style.paragraph_format.line_spacing = Pt(line_spacing_pt)
            style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST

        # Section-name paragraphs get extra space above them; everything else
        # uses the tight base spacing set on the styles above. The reference
        # resume uses none at all -- sections are visually separated by the
        # header's solid background color, not whitespace -- so this is a
        # no-op at section_spacing_pt=0.
        section_name_labels = {s.get("section_name", "").upper() for s in sections}
        for paragraph in document.paragraphs:
            if paragraph.text.strip() in section_name_labels:
                paragraph.paragraph_format.space_before = Pt(section_spacing_pt)

        final_buffer = BytesIO()
        document.save(final_buffer)
        return final_buffer.getvalue()

    def generate_docx(
        self, structured_data: dict, layout_preferences: dict, output_path: str, template_bytes: bytes | None = None
    ) -> bool:
        """Backwards-compatible file writer used by scripts and tests."""
        content = self.generate_docx_bytes(structured_data, layout_preferences, template_bytes)
        Path(output_path).write_bytes(content)
        return True
