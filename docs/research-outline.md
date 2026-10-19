# Research and project report outline

This outline records the requested 26-section report structure. Sections describing the implemented prototype reflect the approved architecture and application code. A source-checked, qualified five-study survey is in [literature-review.md](literature-review.md); verified broad occupational-reference mappings and their limitations are in [catalog-provenance.md](catalog-provenance.md). These citations and sources do not validate this prototype's scores, weights, outputs or outcomes. Empirical results still require real study data; none are fabricated here.

## 1. Abstract
Summarize the research question, intended population, system method, evaluation design and observed results after the study. Do not write numerical claims until a real evaluation run exists.

## 2. Introduction
Describe early-career decision uncertainty and the goal of supporting—not replacing—learner judgment. Add sourced context before submission.

## 3. Problem Statement
Explain the challenge of comparing a learner's editable education, skills, experience, interests and projects with transparent career requirements.

## 4. Objectives
Develop structured profile capture, ranked career suggestions, visible score evidence, gap analysis, editable learning plans and a bounded conversational explanation layer.

## 5. Existing System
Complete with a cited description of career platforms, conventional rule-based recommenders and conversational career tools relevant to the final research question.

## 6. Existing System Limitations
Complete only after source review. Potential dimensions to investigate include opacity, stale role requirements, sparse personalization, unsupported LLM claims and evaluation quality.

## 7. Literature Survey
Use [the verified literature review](literature-review.md), checked 2026-10-07. It records each study's question/context, method, available data, findings, limitations and qualified relevance. Its five sources provide background and methodological cautions, not validation of this system.

## 8. Research Gap
State a narrow, evidence-backed gap only after completing the literature survey. Do not infer novelty from the presence of an LLM alone.

## 9. Proposed System
CareerInsight AI computes recommendation scores from explicit structured profile evidence and an editable role/skill catalogue. The LLM explains only after ranking; optional curated retrieval provides role context.

## 10. System Architecture
Use the flow in [architecture.md](architecture.md): React/TypeScript client → FastAPI REST application → relational user/catalog data → deterministic recommendation and skill-gap services → optional curated retrieval/LLM explanation → persistent roadmap.

## 11. Methodology
Document population, profile fields, consent, catalogue curation, handling of missing data, inclusion/exclusion criteria, data protection, study protocol and evaluation split before collecting study data.

## 12. Recommendation Algorithm
Report the implementation's initial configurable factor weights (skills 35%, interests 25%, projects 15%, education 10%, goal 10%, experience 5%) and mapping rules. Identify these as unvalidated prototype assumptions. Record any later weight changes by version and justify them empirically.

## 13. Explainability Method
For each ranked path, expose factor score, factor weight, factor contribution, known profile evidence, input coverage, matched skills, related projects and missing requirement skills. Label generated prose and distinguish it from deterministic evidence summaries.

## 14. LLM Architecture
Describe the LLM as a language/explanation layer after structured scoring. Document the evidence payload, instruction boundary, model/service configuration, privacy handling, latency/failure fallback and output evaluation for the final experiment.

## 15. RAG Architecture
Describe the optional authored role-note corpus and deterministic skill/tag retrieval. The non-authoritative role notes are prototype guidance, not a universal requirements database. Learning links and per-provider scope notes are stored separately in [`../rag/learning_resources.json`](../rag/learning_resources.json), reviewed 2026-10-07. Map seeded career-role names to official occupational sources and disclose direct versus analogue fit in [catalog-provenance.md](catalog-provenance.md), checked 2026-10-07. The retrieval is not a vector store or live labor-market feed. Record corpus versions, review dates and coverage before external accuracy claims.

## 16. Database Design
Use [schema.md](../database/schema.md) to document normalized records, foreign keys, ownership, indexes, migrations, data retention and the deliberate decision not to persist original resumes by default.

## 17. UI Design
Describe the restrained academic analytics design system, responsive sidebar/workspace, user review steps, transparent evidence panels and accessible controls.

## 18. Implementation
Record framework/runtime versions, repository commit, deployment configuration, API surface, security measures, dependency versions, migration revision and known limitations for the actual evaluated build.

## 19. Experimental Setup
Specify test sources, participant consent where applicable, labeling rubric, baselines, test-set construction, split procedure, evaluation date, software version, excluded/failed cases and reproducibility steps.

## 20. Evaluation Metrics
The API computes macro precision, macro recall, macro F1 and top-3 accuracy from actual labeled cases with predictions supplied for four method variants. It does not train or infer those strategies. It also accepts per-method satisfaction ratings, explanation-usefulness ratings (each 1–5) and measured response times in milliseconds. These optional means are computed only from submitted actual values, with the observation count shown; omit any measure for which no documented collection protocol and real measurements exist.

## 21. Results
Populate only from recorded evaluation runs and the documented study. At present, no research results are asserted. A blank results state is intentional until real labeled data is evaluated.

## 22. Discussion
Interpret actual findings against the protocol and sources after evaluation. Separate observations from speculation and report uncertainty.

## 23. Limitations
Discuss unvalidated initial weights, catalogue scope, coarse education mapping, exact catalogue-field project matching that is not semantically validated, self-reported skills/interests, local role variation, data coverage and limitations of generated explanation.

## 24. Future Work
Potential work includes expert-reviewed dated role requirements, external labor-market validation, calibrated weights, a consent-based user study, fairness/privacy review, stronger retrieval evaluation, and a mobile client using the same REST API.

## 25. Conclusion
Complete after the project is evaluated. Do not assert improved employment outcomes or proven recommendation quality without evidence.

## 26. References
Use the complete verified academic citations in [literature-review.md](literature-review.md) and the per-role official-source links in [catalog-provenance.md](catalog-provenance.md). Check source pages again before academic submission and cite additional sources for any new external claims. No placeholder citation is represented as a real reference.
