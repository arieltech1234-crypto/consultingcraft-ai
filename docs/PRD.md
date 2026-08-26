# Product Requirements Document (PRD): ConsultingCraft AI

## 1. Product Vision & Goals
**Vision:** Democratize access to elite consulting and product management career trajectories by automating the hyper-specific, high-bar resume formatting and styling requirements expected by top firms (e.g., BCG, McKinsey, Bain).
**Goal:** Build an intelligent, multi-modal CV builder that takes raw experience, target Job Descriptions, and Reference CVs to generate a strictly one-page, perfectly formatted, RAC-structured (Result, Action, Context) resume.

## 2. Target Audience
*   **Primary:** College seniors, MBA candidates, and young professionals aiming for Tier 1 consulting (MBB) or AI/Tech PM roles.
*   **Secondary:** Experienced hires looking to pivot into strategy or product roles.

## 3. Discovery Hypotheses & Validation Plan
*   **Current evidence status:** The problem statements below are hypotheses for a student prototype; no representative user study has yet been completed.
*   **Hypothesis 1 (The Time Sink):** Candidates spend material time repeatedly tailoring and formatting role-specific CVs.
*   **Hypothesis 2 (The Strategy Gap):** Candidates struggle to select the most relevant evidence and express it in concise Result-Action-Context (RAC) language.
*   **Validation plan:** Interview 8-12 candidates and 3-5 recruiters or career coaches, then compare the staged workflow against a single-prompt baseline using the experiment plan in this repository.
*   **Product implication:** Treat evidence selection, writing, and physical layout as separate but connected product problems.

## 4. User Pain Points
*   **Formatting Anxiety:** Users spend hours trying to make text fit exactly on one line without trailing whitespace to meet strict consulting norms.
*   **Structural Ignorance:** Candidates struggle to write in RAC/XYZ format or organize their points into MECE (Mutually Exclusive, Collectively Exhaustive) buckets.
*   **Tailoring Fatigue:** Manually tweaking a CV for every specific JD is time-consuming and often done poorly.

## 4. Core Features (MVP)
1.  **Multi-Modal Ingestion:** Ability to upload JDs and Reference CVs in PDF, Docx, or Image (PNG/JPG) formats.
2.  **Smart RAC Generation:** AI drafts bullet points using strong action verbs, ensuring a Result-Action-Context structure.
3.  **MECE Bucketing:** AI logically groups experience (e.g., "Leadership", "Analytical Problem Solving") without overlap.
4.  **Spatial Constraint Optimizer:** An iterative LLM step that targets concise bullet lengths, followed by an explicitly labeled rendered or estimated A4 fit check.
5.  **Customizable Layout Engine:** UI sliders to adjust font size (Arial only), side margins, top/bottom margins, and line/section spacing.

## 6. Success Metrics (Product KPIs)
*   **Output Quality:** Target 90%+ of synthetic regression CVs rendering to one A4 page without text overflow.
*   **Time to Value:** Users generate a tailored CV in under 5 minutes.
*   **Interview Rate (Long-term):** % of users who secure first-round interviews using the tool.

## 7. Ops Diagnostics (Operational Health & LLM Metrics)
To ensure the multi-agent pipeline remains cost-effective and performant, we will monitor the following operational diagnostics:
*   **LLM Latency (P90):** Target <15 seconds for the end-to-end multi-agent pipeline generation.
*   **API Cost per CV:** Target <$0.05 per generated resume by utilizing batch prompting and open-weight models (e.g., Llama 3.1 8B) for high-volume drafting.
*   **Constraint Failure Rate:** The percentage of bullets still outside the configured range after three optimization passes. Initial target < 5%.
*   **Vision Model Fallback Rate:** Tracking how often users trigger the graceful fallback error due to missing vision capabilities, driving product decisions on third-party OCR integrations (e.g., Tesseract).
