"""Fictitious content that makes the public portfolio demo usable without an API key."""

DEMO_PROFILE = {
    "name": "Aarav Mehta",
    "email": "aarav.mehta@example.com",
    "phone": "+91 90000 00000",
    "location": "Bengaluru, India",
    "linkedin": "linkedin.com/in/aarav-mehta-demo",
}

# Hierarchical demo schema, shaped like ai.schema.ResumeSchema
# (sections -> entries -> groups -> bullets), matching what the live pipeline
# produces and what CVGenerator/PageBudgetCalculator expect.
DEMO_RESUME_SCHEMA = {
    "sections": [
        {
            "section_name": "Education",
            "entries": [
                {
                    "header_left": "Indian Institute of Technology (Demo) | B.Tech, Computer Science",
                    "header_right": "2022 - 2026",
                    "summary": "",
                    "groups": [
                        {
                            "group_name": "",
                            "group_summary": "",
                            "bullets": [
                                "Pursuing B.Tech in Computer Science with an 8.7/10 GPA; completed coursework in machine learning, product strategy, and statistics.",
                                "Won a university product case competition by sizing a campus mobility opportunity and presenting an experiment-led launch recommendation.",
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "section_name": "AI product experience",
            "entries": [
                {
                    "header_left": "ConsultingCraft Labs (Demo) | AI Product Intern",
                    "header_right": "May 2025 - Aug 2025",
                    "summary": "",
                    "groups": [
                        {
                            "group_name": "",
                            "group_summary": "",
                            "bullets": [
                                "Built an LLM-powered support triage prototype that classified 1,200 anonymized tickets and reduced manual review time by an estimated 35%.",
                                "Interviewed 12 student users, synthesized four recurring workflow pain points, and translated findings into a prioritized MVP requirements document.",
                                "Designed prompt evaluations across accuracy, latency, and cost; improved grounded response quality from 71% to 86% over three iterations.",
                                "Created a lightweight business case and rollout roadmap for a campus pilot, defining adoption, task-success, and cost-per-resolution metrics.",
                                "Deployed the prototype as a Streamlit application with session-safe document handling, human review controls, and downloadable A4 output.",
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "section_name": "Selected product projects",
            "entries": [
                {
                    "header_left": "Independent Projects (Demo)",
                    "header_right": "",
                    "summary": "",
                    "groups": [
                        {
                            "group_name": "",
                            "group_summary": "",
                            "bullets": [
                                "Benchmarked a single-prompt baseline against a staged evidence workflow, defining factual-preservation and recruiter-preference evaluation rubrics.",
                                "Built an experiment dashboard to compare response quality, latency, and estimated API cost across three prompt configurations.",
                                "Modeled an illustrative campus rollout scenario, sizing adoption and support demand while documenting assumptions and validation risks.",
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "section_name": "Leadership & extracurriculars",
            "entries": [
                {
                    "header_left": "Product Club (Demo) | Team Lead",
                    "header_right": "Aug 2024 - Present",
                    "summary": "",
                    "groups": [
                        {
                            "group_name": "",
                            "group_summary": "",
                            "bullets": [
                                "Led a six-member product club team through discovery and prototyping, shipping a working demo within a four-week sprint.",
                                "Facilitated weekly backlog reviews across design and engineering volunteers, resolving scope trade-offs and delivering 90% of committed stories.",
                                "Coordinated a 60-participant applied AI workshop, translating technical concepts into product decisions, risks, and measurable use cases.",
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "section_name": "Skills & interests",
            "entries": [
                {
                    "header_left": "Skills & interests",
                    "header_right": "",
                    "summary": "",
                    "groups": [
                        {
                            "group_name": "",
                            "group_summary": "",
                            "bullets": [
                                "Product: discovery, PRDs, roadmaps, experimentation | Technical: Python, Streamlit, LLM APIs, SQL | Interests: applied AI and consulting."
                            ],
                        }
                    ],
                }
            ],
        },
    ]
}

DEMO_META = {
    "source_lines": 18,
    "selected_lines": 14,
    "model": "portfolio demo (no API key)",
    "reference_files": 0,
    "constraint_exceptions": 0,
    "pipeline": [
        "In-memory document ingestion",
        "Section mapping and evidence selection",
        "RAC bullet drafting",
        "Constraint optimization",
        "Human review and A4 fit check",
    ],
}
