from io import BytesIO

from docx import Document

from demo_content import DEMO_PROFILE, DEMO_SECTIONS
from layout.generator import CVGenerator
from layout.page_budget import PageBudgetCalculator


PREFERENCES = {
    "font_size": 10,
    "side_margin_inches": 0.55,
    "top_margin_inches": 0.5,
    "bottom_margin_inches": 0.5,
    "line_spacing_pt": 11,
    "section_spacing_pt": 6,
    "sub_section_spacing_pt": 2.5,
}


def test_generated_document_is_a4_and_contains_profile():
    structured = {
        "name": DEMO_PROFILE["name"],
        "contact_line": DEMO_PROFILE["email"],
        "experience_buckets": DEMO_SECTIONS,
    }
    content = CVGenerator().generate_docx_bytes(structured, PREFERENCES)
    document = Document(BytesIO(content))
    section = document.sections[0]
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert abs(section.page_width.mm - 210) < 0.2
    assert abs(section.page_height.mm - 297) < 0.2
    assert DEMO_PROFILE["name"] in text
    assert "AI PRODUCT EXPERIENCE" in text
    assert len(content) > 5_000


def test_demo_content_estimates_to_one_page():
    report = PageBudgetCalculator(PREFERENCES).estimate_fit(DEMO_SECTIONS)
    assert report["fits_one_page"] is True
    assert report["estimated_pages"] == 1
    assert 0 < report["utilization"] < 1


def test_long_content_is_flagged_as_multiple_pages():
    long_sections = {
        "Experience": [
            " ".join(["Delivered measurable product impact"] * 18)
            for _ in range(35)
        ]
    }
    report = PageBudgetCalculator(PREFERENCES).estimate_fit(long_sections)
    assert report["fits_one_page"] is False
    assert report["estimated_pages"] > 1
