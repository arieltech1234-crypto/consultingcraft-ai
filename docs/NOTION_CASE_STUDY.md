# ConsultingCraft AI: Agentic CV Builder

*An AI Product Management Case Study aligning with BCG X*

---

## ?? Overview
**ConsultingCraft AI** is a production-grade, multi-agent AI application designed to transform unstructured "Master CVs" into highly tailored, structurally perfect resumes (specifically targeting the strict ISB template format). 

Rather than just building a slide deck about AI, I rapidly prototyped and shipped a functional AI product using **vibe coding** and LLM-assisted engineering. This project bridges the gap between structured business logic and bleeding-edge AI execution.

## ?? The "Agentic" Architecture
This isn't a simple wrapper around an LLM. It uses a **multi-agent pipeline** powered by Groq and Llama-3/Qwen to handle complex reasoning, extraction, and constraint optimization:

1. **Section Mapper (The Structurer)**
   - **The Problem:** LLMs hallucinate custom buckets (e.g., inventing "Project A" or "Operations").
   - **Agentic Solution:** The Section Mapper chunks the Master CV and maps raw evidence into a deeply nested Pydantic schema (`ResumeSchema`), strictly enforcing 4 required buckets: *Education*, *Internship*, *Work Experience*, and *Extracurriculars*.
2. **Bullet Selector (The Strategist)**
   - Prioritizes high-signal evidence based on target page budgets and job description requirements.
3. **Bullet Drafter (The Executioner)**
   - Drafts points into a strict Result-Action-Context format.
4. **Constraint Optimizer (The Editor)**
   - A multi-pass agent that iteratively edits drafted bullets until they satisfy strict word-count boundaries and formatting rules, minimizing "hallucination drift".

## ??? Vibe Coding & Rapid Prototyping
Aligning with BCG X's culture of "strategy meets build," I utilized AI-assisted coding tools to rapidly iterate on this product:
- **Fast Iteration:** Rebuilt the entire data structure from a flat text list to a deeply nested hierarchical schema in a single day.
- **Solving Edge Cases:** Engineered chunking and sleep-delay mechanisms to bypass Groq's Token-Per-Minute (TPM) limits when processing massive resumes.
- **Continuous Deployment:** Migrated the app from a local environment to **Render.com** (via GitHub) to bypass corporate HSTS/SSL VPN intercepts, ensuring the product is accessible to users anywhere.

## ?? Product Artefacts & Strategy
Throughout the lifecycle of this build, I owned the core product artefacts:
- **PRD & Strategy:** Defined the initial scope, target audience (consulting candidates), and success metrics.
- **Roadmap & Backlog:** Managed the pivot from a simple text generator to a strict `docxtpl` Jinja injection engine when user feedback demanded pixel-perfect Word Document layouts.
- **User Experience (UX):** Designed an interactive Streamlit UI that allows users to *Review*, *Rewrite*, and *Remove* AI-generated sections before finalizing the export.

## ?? Why This Matters for BCG X
This project demonstrates my ability to **structure ambiguous problems** (turning chaotic resume text into a strict Pydantic JSON schema) and **build real AI products** (deploying a functional, multi-agent pipeline). It reflects the exact blend of product strategy and hands-on "vibe coding" required to co-create AI-powered solutions at BCG X.
