# Portfolio case study: ConsultingCraft AI

## One-line summary

I designed and built an evidence-led CV tailoring prototype that combines
role-specific LLM assistance, human review, and transparent A4 layout checks.

## Problem framing

The user is a student or early-career candidate with a large master CV who must
produce a concise version for a specific role. The hard part is not generating
more prose; it is selecting defensible evidence, connecting it to role signals,
and managing a strict page budget without inventing achievements.

## Discovery status

The current problem statements are hypotheses, not validated research findings.
The next discovery sprint will interview 8-12 candidates and 3-5 recruiters or
career coaches. Research artefacts and anonymized synthesis should be added
before claiming measured user pain.

## Product decisions

### Separate selection from rewriting

A single prompt can produce fluent but weakly grounded output. The staged
workflow first maps and selects source evidence, then drafts and optimizes it.

### Keep a human approval step

Generated bullets can change emphasis or introduce ambiguity. The export is
therefore downstream of an explicit editing step.

### Trade a guarantee for transparency

DOCX pagination varies by renderer and installed fonts. The product performs a
rendered page check where LibreOffice is available and otherwise shows a
labeled estimate. This is more trustworthy than claiming deterministic fit.

### Make the portfolio demo independent of infrastructure

Recruiters can explore the product without an API key, external calls, or real
candidate data. Live AI mode remains available for deeper testing.

## MVP scope

- DOCX and PDF master-CV ingestion
- optional job-description and reference inputs
- role-aware section mapping and evidence selection
- RAC-style drafting and iterative length optimization
- editable review surface
- in-memory A4 DOCX export
- fit-report method disclosed to the user

## Non-goals

- autonomous application submission
- storing candidate accounts or documents
- making hiring-outcome promises
- reproducing proprietary employer templates or branding

## Success measures

| Metric | Prototype target | Measurement |
|---|---:|---|
| Factual preservation | >=95% | Blind comparison with source evidence |
| Recruiter preference | >=60% vs single-prompt baseline | Paired rating test |
| One-page render pass | >=90% | Rendered DOCX regression set |
| Median time to first useful draft | <5 minutes | Instrumented usability test |
| Constraint exception rate | <5% | Pipeline logs, excluding manual edits |

These are targets for validation, not achieved results.

## What I would do next

1. Run the baseline comparison in `EXPERIMENT_PLAN.md`.
2. Add a small golden dataset of synthetic CV/JD pairs.
3. Introduce structured LLM outputs and citation links from each bullet to its
   originating evidence line.
4. Add cost and latency instrumentation.
5. Test export consistency across Microsoft Word, LibreOffice, and Google Docs.

## Interview walkthrough

Start with the user problem, show the no-key demo, edit one bullet, export the
DOCX, and then explain one product trade-off: evidence selection before
generation, privacy versus persistence, or transparent estimation versus a
false guarantee.
