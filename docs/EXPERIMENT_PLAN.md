# Experiment plan

## Decision to inform

Does the staged evidence-selection workflow create more useful and trustworthy
role-tailored bullets than a single-prompt baseline?

## Hypothesis

Candidates and recruiters will prefer staged-workflow outputs because they are
more role-relevant while preserving source facts.

## Test design

- Build 10 fully synthetic master-CV and job-description pairs.
- Generate one output with a single prompt and one with ConsultingCraft AI.
- Randomize and blind the outputs.
- Ask 3-5 recruiters or career coaches to score relevance, clarity, evidence,
  and interview usefulness on a five-point rubric.
- Independently audit every claim against the synthetic source CV.

## Primary metric

Percentage of paired evaluations in which the staged workflow receives the
higher overall usefulness score.

## Guardrail metrics

- unsupported fact rate
- time to first useful draft
- API cost per completed draft
- P90 end-to-end latency
- percentage of DOCX files that render to one A4 page

## Success threshold

Proceed to a limited candidate pilot if the workflow wins at least 60% of
paired ratings and unsupported claims remain below 5%.

## Risks

- evaluator preferences may reflect writing style rather than usefulness
- synthetic inputs may be cleaner than real master CVs
- a small expert sample will produce directional, not conclusive, evidence
