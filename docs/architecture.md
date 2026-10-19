# Architecture and methodology

## Data flow

```text
Authenticated user profile + interests + projects
                     ↓
         Structured career catalogue
                     ↓
      Configurable deterministic scoring
                     ↓
 Ranked roles + factor contributions + evidence
          ↙                           ↘
Skill-gap computation             Optional curated retrieval
          ↘                           ↙
           Evidence-grounded explanation / coach
                     ↓
            Persistent learning roadmap
```

The LLM is not permitted to rank roles, determine the match score, or invent candidate evidence. The scoring service returns roles in descending deterministic score order. Explanation requests carry the computed score, factor values/weights, matched and missing skills, projects, evidence coverage and curated role notes. If the optional platform LLM call is not usable, the API returns a deterministic evidence-based summary and marks `ai_generated: false`.

## Initial score

For each career, factor values are normalized on a 0–100 scale. The initial score is:

`0.35 × skill match + 0.25 × interest match + 0.15 × project match + 0.10 × education match + 0.10 × career-goal match + 0.05 × experience match`.

Weights are stored as backend scoring settings and normalized by their sum. Their values are initial configurable project assumptions; no scientific validation is claimed. Current skill levels map to ordinal values (beginner 1, intermediate 2, advanced 3); role requirements identify a required level and importance. The skill factor aggregates capped current-to-required ratios, weighted by role importance. Missing values remain distinguishable from confirmed profile evidence, and the response reports profile coverage. Where a factor lacks user input, the prototype uses an explicit neutral value and emits an “unknown/not provided” evidence note rather than claiming that the user lacks the attribute.

Interest alignment uses only explicitly user-selected entries from the seeded assessment list and controlled role-specific mappings. Project alignment matches exact catalogue skills/tools, exact industry tags in the project-domain field, and phrases explicitly listed as typical role projects; it does not reward generic word overlap. Unmatched projects receive a neutral score. Education and experience are interpreted from submitted values and the seeded requirements. These mappings are transparent prototype rules, not validated psychometric or labor-market models.

## Career catalogue

The seed catalogue contains Data Analyst, Data Scientist, Machine Learning Engineer, AI Engineer, Data Engineer, Software Developer, Full Stack Developer, Cybersecurity Analyst, Cloud Engineer and Business Analyst. Role requirements live in the relational `career_roles` and `career_skills` tables and connect to normalized `skills`. Role descriptions, education guidance, tool lists, example project types and industry tags are seedable data, designed to be extended without modifying React code.

## Persistence and boundaries

FastAPI owns authentication, authorization, profile/user-owned records, career ranking, gaps, roadmap progress and research metrics. SQLAlchemy is the persistence abstraction; managed development/production uses MySQL and local standalone development can use SQLite. Alembic owns versioned schema changes. `user_id` ownership is checked on profile, roadmap and coach paths. Uploaded documents are parsed in memory; only accepted extraction data and limited resume metadata are stored by default.

The React/TypeScript client calls relative REST routes. The same contracts are independent of the SPA and can later support a React Native app. The API schema is published as OpenAPI at `/openapi.json`.

## Optional retrieval and LLM use

A curated authored role catalogue provides occupation-context guidance; a separate dated set of provider-verified learning-resource links lives in `rag/learning_resources.json`. Retrieval is deterministic skill/tag matching (not a vector embedding service) and returns only records already in these files. LLM messages explicitly separate profile evidence from non-personal catalogue notes, qualify those role records as prototype guidance, prohibit unsupported claims and invented links, and state that ranking is already computed. The system stores the response and returned resource metadata in account-scoped chat history. The displayed links point to their providers; the generated response is not a comprehensive literature citation and the application has no live labor-market feed.

## Limitations

The initial rules and weights are an engineering prototype, not validated against hiring outcomes, representative survey data or a calibrated recommendation benchmark. No trained machine-learning predictor or representative labeled training cohort was supplied; research evaluation accepts externally produced method predictions and does not train/infer them. The skill taxonomy and role catalogue need expert review and dated source citations. Interest selection is self-reported, education matching is intentionally coarse, and exact catalogue-field project matches are not a validated measure of semantic relevance. The prototype must not be used to screen, hire or exclude people. Recommendations are exploratory decision support and may omit local, emerging or specialized roles.
