# CareerInsight AI — Implementation outcomes

This outcome tracker preserves the approved acceptance clauses. `[x]` indicates implemented and backed by the current integration/build/migration checks; `[ ]` marks work that remains dependent on real study data or external configuration, not fabricated in this build.

## 1. Public product experience and visual system
- [x] Build a professional landing page for “CareerInsight AI” with navigation Home, How It Works, Features, Research, About and Login, plus the “Get Started” CTA.
- [x] Use the title “Make Better Career Decisions with Explainable AI” and explain that the platform analyzes skills, interests, education and goals to recommend personalized career paths and learning strategies.
- [x] Include “Start Career Analysis” and “Explore How It Works” actions and a restrained User Profile → AI Analysis → Career Recommendation → Skill Roadmap visualization; do not use a giant chatbot illustration.
- [x] Show the four process steps: “Build Your Profile,” “Tell Us Your Interests,” “AI Analyzes Your Profile,” and “Receive Personalized Recommendations.”
- [x] Maintain the requested classy, formal, professional, academic, research-oriented and trustworthy university/research SaaS style; do not style it as gaming, flashy AI, crypto, social media or neon/cyberpunk.
- [x] Use the specified deep navy #16324F, slate blue #3E5C76, muted teal #2A7F7F, warm off-white #F7F8FA, white cards, text #1F2937/#64748B, borders #E2E8F0 and restrained success/warning/error colors. Avoid bright purple, neon blue/green, excessive gradients, glowing cards, excessive animation, decorative graphics and unnecessary 3D.
- [x] Use readable Inter (or Manrope) typography, clear heading/body/label hierarchy, white structured cards, thin borders, subtle shadows, consistent spacing, 10–14px radii, accessible controls and professional restrained charts.

## 2. Authentication, profile setup and preferences
- [x] Provide Login, Register, Forgot Password and Reset Password workflows. Login has email, password and Remember Me; registration has full name, email, password, confirm password, education, degree, branch and graduation year.
- [x] After registration route to Profile Setup; after login route incomplete profiles to Profile Setup and complete profiles to Dashboard.
- [x] Collect name, education, degree, branch and graduation year; programming languages, tools, frameworks, databases and AI/ML skills; communication, leadership, problem solving and teamwork; Beginner/Intermediate/Advanced experience (including an explicit not-provided state); project name/description/technologies/domain; certification name/platform/year; target role and preferred industry.
- [x] Implement secure password hashing, authenticated and authorized API access, validated input, protected endpoints and per-user data ownership. Keep API keys out of frontend code and use environment variables for credentials. Apply account-keyed request limits to registration, login, password reset, resume upload, AI chat and researcher evaluation.
- [x] Keep password-reset tokens hidden until SMTP is configured; do not expose tokens in browser responses or logs as a delivery substitute. Explain when reset delivery is unavailable.
- [x] Allow users to update their preferences and correct their profile; subsequent analysis must use the updated information.

## 3. User-stated and inferred interest assessment
- [x] Do not assume a user's interests. Provide a short professional assessment with multiple selections about enjoyed work, problems to solve, technologies and preferred projects, including options such as data, software, AI, cybersecurity, cloud, business analysis and research. Accept only exact seeded assessment choices; reject unknown choices without deleting saved selections.
- [x] Generate an editable interest profile. Distinguish user-provided interests from AI-inferred interests and never state an inference as a confirmed fact. This build records user-stated interests; it does not fabricate inferred interests.

## 4. Resume processing and review
- [x] Allow PDF and DOCX uploads with file validation and size restrictions. Extract skills, education, projects, certifications and text excerpts from identified experience sections; do not infer or change the user's experience level from resume dates or prose.
- [x] Show detected information before saving and provide Accept, Edit and Reject actions. Never silently store unreviewed or incorrect extracted information.

## 5. Career knowledge base and recommendation engine
- [x] Keep a structured, extensible career dataset for Data Analyst, Data Scientist, Machine Learning Engineer, AI Engineer, Data Engineer, Software Developer, Full Stack Developer, Cybersecurity Analyst, Cloud Engineer and Business Analyst.
- [x] Each career has required and preferred skills, skill importance, education, tools, typical projects and beginner/intermediate/advanced requirements.
- [x] Compute and rank recommendations from structured user/career data, not from LLM-generated scores or hard-coded UI values. Initial configurable assumptions: Skill Match 35%, Interest Match 25%, Project Match 15%, Education Match 10%, Career Goal Match 10%, Experience Match 5%.
- [x] Make factor weights configurable from the backend and do not claim they are scientifically validated. Show score generation, factor scores, supporting evidence and missing skills for multiple ranked careers.
- [x] Match interests with controlled role-specific catalogue mappings. Match projects using exact catalogue skill/tool/industry fields or listed typical-project phrases; do not credit generic shared words, and use the documented neutral score when no specific project catalogue field matches.
- [x] Calculate skill gaps against career requirements and update scores, gaps and dashboard values from actual current backend data.
- [x] Keep recommendation logic in backend services, independent from React components, behind versionable REST APIs for future React Native/Expo clients.

## 6. Dashboard, explanations and skill gaps
- [x] Provide the authenticated premium professional dashboard with personalized greeting and analysis summary; display career match, skill match, career readiness and skill-gap count based on backend results.
- [x] Show the top recommendation, match score, Skill/Interest/Project/Education breakdown, an explanation action, matched evidence (including relevant user skills, interests and projects), missing skills, horizontal skill progress bars, alternative careers, personalized roadmap and next-best action.
- [x] Provide a dedicated “Why This Recommendation?” view with overall match, every weighted factor, matched skills, missing skills, relevant projects, interest alignment, education alignment and the generated explanation.
- [x] Clearly label generated prose “AI-generated explanation.” Generate it only from structured evidence; the LLM must not invent skills, projects, experience, interests or career requirements.
- [x] Provide a dedicated skill-gap page with selected career, required skill, current level, required level, gap/severity and “Recommended Next Skills.”

## 7. Personalized roadmap and progress
- [x] Generate a personalized roadmap with Foundation (Python, SQL, Statistics), Core Skills (Machine Learning, Data Visualization), Projects (Project 1, Project 2), Portfolio (GitHub, Resume, LinkedIn), and Career Preparation (Mock Interviews, Applications, Internships), adapted to actual profile and career gaps.
- [x] Each roadmap item has status, description and a completion control. Persist progress in the database and restore it on subsequent visits; provide a dated, source-linked learning resource where a reviewed match exists.

## 8. AI Career Coach and optional grounded retrieval
- [x] Provide a clean formal contextual AI Career Coach, not a generic ChatGPT clone, using the authenticated user's profile and computed recommendation context.
- [x] Include suggested prompts “Explain my recommendation,” “Show my skill gaps,” “Create my learning plan,” “Suggest a project,” and “Compare my top two careers.” Load the account's persisted user/assistant chat history, persist cited resource links with assistant replies, restrict history reads/deletion to its owner, and require confirmation before clearing it.
- [x] Use the LLM for natural-language understanding, evidence-based explanations, personalized roadmap support, career coaching, resume understanding and follow-up questions only where appropriate; do not let it determine career scores.
- [x] The coach must not guarantee employment, make unsupported claims, invent user information or make discriminatory recommendations.
- [x] Optional RAG uses a curated career knowledge base for descriptions, required skills, industry information, roles and learning resources; it must ground advice and not invent career requirements. Keep all seeded career requirement records labeled as prototype guidance. Link the reviewed provider/title/URL learning resources in the roadmap and relevant coach replies; retain their review date and per-source scope notes. If AI service output is unavailable, communicate this and use a safe evidence-based fallback rather than pretending it was generated.

## 9. Research/evaluation, ethics and documentation
- [x] Provide a research/evaluation section accessible only to authorized users. Show actual evaluation results only; do not fabricate precision, recall, F1, top-K accuracy, satisfaction, explanation usefulness or response-time values. Require labeled cases to use a seeded career slug/name and contain submitted ranked predictions for baseline, ML, ML+LLM, and ML+RAG+LLM; calculate macro precision, macro recall, macro F1 and top-3 accuracy from those actual submissions. Optional satisfaction and explanation-usefulness measurements are 1–5; optional response-time measurements are actual milliseconds. Compute each mean only from submitted observations and store its sample count; leave omitted measures absent, never zero-filled. The evaluation endpoint must not invent method predictions or claim to train/infer models.
- [x] When actual test data/results exist, support comparison of Baseline Recommendation, ML Recommendation, ML + LLM Explanation, and ML + RAG + LLM by evaluating submitted genuine predictions. The evaluation engine does not itself train/infer those strategies.
- [x] Prepare project documentation covering Abstract, Introduction, Problem Statement, Objectives, Existing System, Existing System Limitations, Literature Survey, Research Gap, Proposed System, System Architecture, Methodology, Recommendation Algorithm, Explainability Method, LLM Architecture, RAG Architecture, Database Design, UI Design, Implementation, Experimental Setup, Evaluation Metrics, Results, Discussion, Limitations, Future Work, Conclusion and References. Cite the source-checked academic survey and dated official role-provenance map, label analogues as analogues, re-check sources before academic publication, and do not claim the citations validate this prototype's scores, requirements or outcomes.
- [x] Display exactly: “Career recommendations are decision-support suggestions and should not be treated as guaranteed career outcomes.” Avoid sensitive personal attributes, allow profile correction and store only necessary information.
- [ ] Train and validate a real ML career predictor and report comparative experiment results only after a representative, appropriately consented and labeled research dataset, study protocol and outcome labels are supplied. No such dataset was supplied for this build; `ml/README.md` records this limitation.

## 10. Persistent architecture, security, responsiveness and handoff
- [x] Implement the approved React/TypeScript frontend and Python FastAPI backend with managed relational persistence, structured career/profile records, a frozen explicit initial Alembic schema snapshot, additive later migrations, foreign keys, indexes and durable roadmap progress.
- [x] Keep schema auto-creation off by default so local and production startup do not mark Alembic revisions complete without applying their operations; run migrations before local app startup and keep any auto-create opt-in limited to disposable databases.
- [x] Provide the requested API routes: POST /auth/register, /auth/login, /auth/logout; GET/PUT /profile; POST/GET /interests; POST /resume/upload; POST /career/analyze; GET /career/recommendations; GET /career/{id}; GET /career/{id}/explanation; GET /skills/gaps; POST /roadmap/generate; PUT /roadmap/progress; POST /ai/chat.
- [x] Make the site responsive on desktop, laptop, tablet and mobile; on mobile the sidebar becomes a mobile navigation menu, dashboard cards stack vertically and charts resize correctly.
- [x] Include README.md, .env.example, API documentation, database schema, setup guide and deployment guide, with clear Windows setup instructions. Keep the requested frontend/, backend/, database/, ml/, llm/, rag/, docs/ and tests/ structure.
- [x] Use realistic seed/demo data for development, but generate demo recommendations by executing the recommendation engine; do not hard-code fake recommendation results into the UI.
- [x] Ensure important buttons work, forms validate, dashboard values come from backend data, skill gaps are calculated from career requirements, LLM explanations use structured evidence, and roadmap progress persists.
- [x] Keep architecture extendable to Android, iOS, research prototype, conference/journal paper and production SaaS.

## Validation evidence
- `./.venv/bin/python tests/test_api.py`: 9 integration tests passed, including registration/profile/scoring, researcher evaluation, resume review/removal, experience excerpts, catalog-only interests, rate limiting, CSRF, saved coach resource history and migration-first startup defaults.
- `npm run build` in `frontend/`: passed after final chunk splitting with no chunk-size or circular-chunk warnings.
- `python -m compileall -q backend tests`: passed.
- Fresh SQLite Alembic checks: revision `0001` verified with non-null experience and no chat-resource column; upgrading through `0002`/`0003` verified nullable experience and the `chat_history.resources` column.
- Fresh migrated SQLite startup with auto-creation unset is verified to leave the database at Alembic head rather than bypassing the revision table.
- Managed-database Alembic upgrade completed from `0002_nullable_experience_level` to `0003_chat_message_resources (head)`.
- Current built-in Manus LLM path returned usable output in a non-sensitive smoke call.
- Public Preview returned HTTP 200 for `/`, the transformed React module, `/manus-routes.json` and `/api/healthz`; the exact route manifest and required landing copy were present; `auth/me` issued a `Secure; SameSite=None` CSRF cookie.
