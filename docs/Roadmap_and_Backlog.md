# Product Roadmap & Agile Sprint Backlog

> Status note: the privacy-safe portfolio MVP is implemented. Monetization,
> authentication, institutional features, and measured outcome claims remain
> future work.

## 1. Product Roadmap (Now, Next, Later)

### 🔴 NOW (Q1: The MVP Core)
*   **Goal:** Prove the core value proposition: spatial awareness + RAC structuring.
*   **Key Deliverables:**
    *   Streamlit UI for rapid prototyping and internal testing.
    *   Multi-agent AI pipeline (Ingester -> Analyzer -> Drafter -> Constraint Optimizer).
    *   Docx generation engine locking in strict Arial font and exact margin calculations.

### 🟡 NEXT (Q2: User Experience & Monetization)
*   **Goal:** Transition from a prototype to a consumer-grade web application and introduce the premium tier.
*   **Key Deliverables:**
    *   Migrate from Streamlit to a Next.js + React frontend for a smoother, drag-and-drop user experience.
    *   Stripe integration for processing $19.99/mo premium subscriptions.
    *   "Live Preview" pane showing the CV updating in real-time as the Constraint Optimizer runs.
    *   Integration with third-party OCR (e.g., Tesseract/AWS Textract) as a fallback for missing LLM vision models.

### 🟢 LATER (Q3+: Enterprise & B2B Expansion)
*   **Goal:** Expand SAM by offering B2B solutions to University Career Centers.
*   **Key Deliverables:**
    *   Admin dashboard for career center coaches to track student usage and review generated CVs.
    *   SSO Integration (SAML/OAuth) for University domains.
    *   Automated Cover Letter Generation matching the exact tone of the optimized CV.

---

## 2. Sprint 1 Backlog & User Stories

**Sprint Goal:** Ensure the Constraint Optimizer agent accurately manipulates word counts to prevent text overflow.

### Story 1: Intelligent Word Count Iteration
**As a** user targeting MBB,
**I want** my bullet points to fit exactly on one line without awkward text wrapping,
**So that** my CV adheres to strict consulting aesthetic standards.

*   **Acceptance Criteria 1:** The `ConstraintOptimizer` agent must receive the target minimum and maximum word counts dynamically based on the user's selected side-margin width.
*   **Acceptance Criteria 2:** If a generated bullet point exceeds the maximum word count, the agent must rewrite it to be shorter without losing the core "Result" metric.
*   **Acceptance Criteria 3:** The optimization loop must terminate automatically if all bullets pass the constraint check, OR it hits a hard limit of 3 iterations (to prevent infinite API loops and high latency).

### Story 2: Graceful Vision Model Degradation
**As an** end-user uploading a screenshot of a JD,
**I want** the system to tell me immediately if it cannot process images,
**So that** I know to upload a PDF instead of waiting for a silent failure.

*   **Acceptance Criteria 1:** The `DocumentIngester` must dynamically query the LLM provider for active vision models and process uploads without shared-disk persistence.
*   **Acceptance Criteria 2:** If no vision model is found (e.g., due to deprecation), the system must immediately halt the pipeline and display a user-facing error recommending PDF/Docx upload.
*   **Acceptance Criteria 3:** The error must not trigger a crash in the downstream `ReferenceAnalyzer` agent.
