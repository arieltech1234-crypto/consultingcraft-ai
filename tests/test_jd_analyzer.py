from ai.jd_analyzer import classify_reference_text, compute_jd_coverage


JD_TEXT = """
About the role
We are looking for a Product Analyst to join our team.

Responsibilities
- Own the roadmap for a core feature area
- Partner with engineering and design

Minimum qualifications
- 2+ years of experience in product analytics
- Proficiency in SQL and Python

Equal opportunity employer.
"""

RESUME_TEXT = """
Jane Doe
jane@example.com | linkedin.com/in/janedoe

EDUCATION
State University | B.S. Computer Science
2019 - 2023
GPA: 3.8/4.0

WORK EXPERIENCE
Acme Corp | Product Analyst
2023 - Present
- Delivered a 12% lift in activation by redesigning the onboarding funnel
- Partnered with engineering to ship three experiments per quarter

SKILLS & INTERESTS
Python, SQL, product analytics
"""


def test_classifies_job_description():
    assert classify_reference_text(JD_TEXT) == "jd"


def test_classifies_reference_resume():
    assert classify_reference_text(RESUME_TEXT) == "resume"


def test_compute_jd_coverage_splits_covered_and_missing():
    jd_requirements = {
        "required_skills": ["SQL", "Stakeholder management"],
        "keywords": ["roadmap", "activation"],
    }
    schema = {
        "sections": [
            {
                "entries": [
                    {
                        "groups": [
                            {"bullets": ["Improved activation using SQL dashboards."]}
                        ]
                    }
                ]
            }
        ]
    }
    coverage = compute_jd_coverage(schema, jd_requirements)
    assert coverage["total"] == 4
    assert set(coverage["covered"]) == {"SQL", "activation"}
    assert set(coverage["missing"]) == {"Stakeholder management", "roadmap"}


def test_compute_jd_coverage_with_no_requirements_is_empty():
    coverage = compute_jd_coverage({"sections": []}, {})
    assert coverage == {"covered": [], "missing": [], "total": 0}
