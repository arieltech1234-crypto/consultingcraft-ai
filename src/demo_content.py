"""Fictitious content that makes the public portfolio demo usable without an API key."""

DEMO_PROFILE = {
    "name": "Aarav Mehta",
    "email": "aarav.mehta@example.com",
    "phone": "+91 90000 00000",
    "location": "Bengaluru, India",
    "linkedin": "linkedin.com/in/aarav-mehta-demo",
}

DEMO_SECTIONS = {
    "Education": [
        "Pursuing B.Tech in Computer Science with an 8.7/10 GPA; completed coursework in machine learning, product strategy, and statistics.",
        "Won a university product case competition by sizing a campus mobility opportunity and presenting an experiment-led launch recommendation.",
    ],
    "AI product experience": [
        "Built an LLM-powered support triage prototype that classified 1,200 anonymized tickets and reduced manual review time by an estimated 35%.",
        "Interviewed 12 student users, synthesized four recurring workflow pain points, and translated findings into a prioritized MVP requirements document.",
        "Designed prompt evaluations across accuracy, latency, and cost; improved grounded response quality from 71% to 86% over three iterations.",
        "Created a lightweight business case and rollout roadmap for a campus pilot, defining adoption, task-success, and cost-per-resolution metrics.",
        "Deployed the prototype as a Streamlit application with session-safe document handling, human review controls, and downloadable A4 output.",
    ],
    "Selected product projects": [
        "Benchmarked a single-prompt baseline against a staged evidence workflow, defining factual-preservation and recruiter-preference evaluation rubrics.",
        "Built an experiment dashboard to compare response quality, latency, and estimated API cost across three prompt configurations.",
        "Modeled an illustrative campus rollout scenario, sizing adoption and support demand while documenting assumptions and validation risks.",
    ],
    "Leadership & extracurriculars": [
        "Led a six-member product club team through discovery and prototyping, shipping a working demo within a four-week sprint.",
        "Facilitated weekly backlog reviews across design and engineering volunteers, resolving scope trade-offs and delivering 90% of committed stories.",
        "Coordinated a 60-participant applied AI workshop, translating technical concepts into product decisions, risks, and measurable use cases.",
    ],
    "Skills & interests": [
        "Product: discovery, PRDs, roadmaps, experimentation | Technical: Python, Streamlit, LLM APIs, SQL | Interests: applied AI and consulting."
    ],
}

DEMO_META = {
    "source_lines": 18,
    "selected_lines": 14,
    "pipeline": [
        "In-memory document ingestion",
        "Section mapping and evidence selection",
        "RAC bullet drafting",
        "Constraint optimization",
        "Human review and A4 fit check",
    ],
}
