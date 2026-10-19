# CareerInsight AI

**An explainable LLM-powered decision-support prototype for personalized career paths and skill recommendations.** The system computes ranked career matches from structured profile evidence first; the LLM is only an optional explanation and coaching layer. Recommendations are suggestions—not guaranteed career outcomes.

## Architecture

- `frontend/`: React 18, TypeScript and Vite single-page app; same-origin API calls to `/api`.
- `backend/`: Python FastAPI REST application; SQLAlchemy models, account/session security, resume parsing, recommendation/gap/roadmap services and optional evidence-grounded LLM calls.
- `backend/models/`: relational entities and ownership keys. `backend/migrations/`: Alembic migrations.
- `database/`, `ml/`, `llm/`, `rag/`, `docs/`, `tests/`: schema/method notes, scoring, safe generation/retrieval, the verified literature review and career-catalog provenance, and checks.
- Webdev Preview uses Vite on port 3000 and the API on port 8000. A production container builds the SPA and serves it together with FastAPI on `PORT` (default 3000).

The managed Webdev database is MySQL-compatible and arrives as `DATABASE_URL`. If that variable is absent for standalone local work, the API uses `sqlite:///./careerinsight.db`. The career/skill catalogue is seeded idempotently; startup does not replace learner data. Roadmap items and completion state are persisted.

## Local development

### Windows (PowerShell)

1. Install Python 3.12 and Node.js 22 (npm 10.9.2 or compatible).
2. From the repository root, create and activate an environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
       python -m pip install -r requirements.txt
       Copy-Item .env.example .env
       python -m alembic upgrade head
   ```

3. Leave `DATABASE_URL` blank to use the local SQLite database. For plain `http://localhost`, set `COOKIE_SECURE=false` and `COOKIE_SAMESITE=lax` in `.env`; these are explicit local-only cookie settings. Do not copy them to public HTTPS deployment.
4. Install frontend packages and start both FastAPI and Vite from one PowerShell window:

   ```powershell
   npm --prefix frontend ci
   npm --prefix frontend run dev
   ```

5. Open `http://localhost:3000`. FastAPI's interactive API documentation is at `http://localhost:8000/docs`; the health endpoint is `http://localhost:8000/healthz`.

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
npm --prefix frontend ci
npm --prefix frontend run dev
```

The combined `npm run dev` command starts FastAPI on port 8000 and Vite on port 3000; do not start a duplicate API process. `.env` is loaded for local development, with host-injected settings taking precedence. `.env.example` documents the variables; do not place production secrets in source control.

## Database and migrations

The application defines foreign keys and indexes for users, profiles, skills, user skills, interests, user interests, roles, career skills, projects, resumes, recommendations, skill gaps, roadmaps/progress, chat history, scoring settings, password resets, sessions and evaluation runs. Alembic revision `0001` is a frozen schema snapshot; `0002` makes unprovided experience explicitly nullable; and `0003` adds persisted coach-resource metadata. Later schema changes belong in additive revisions rather than dynamic `create_all` calls. To apply the migration chain explicitly:

```bash
python -m alembic upgrade head
```

Schema auto-creation is disabled by default so Alembic migrations remain authoritative. Local setup runs `alembic upgrade head` before startup. Set `CAREERINSIGHT_AUTO_CREATE=true` only for a disposable database that will not also be managed with Alembic. Production sets it false and runs `alembic upgrade head` before Uvicorn. Managed Preview and publication point at the same Webdev database; use only additive, reviewed migrations and do not treat Preview as an isolated database.

## Accounts, mail and research authorization

Registration requires an email and a password of at least 10 characters. Passwords are hashed with Argon2. Application sessions are opaque, revocable, database-backed cookies; protected state changes require a CSRF token. Public HTTPS defaults to `Secure; SameSite=None`; set `COOKIE_SECURE=false` and `COOKIE_SAMESITE=lax` only for plain-HTTP local development.

Password-reset responses never reveal a token. Reset delivery becomes available only when SMTP and `PUBLIC_APP_URL` are configured in the server environment (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS`, `PUBLIC_APP_URL`). Otherwise the UI clearly reports that delivery is unavailable.

Research pages and evaluation APIs are restricted server-side to accounts registered with an email in `RESEARCH_ADMIN_EMAILS` (comma-separated environment value). The user cannot elevate their own role through a profile form. Evaluation metrics are absent until an authorized user submits labeled cases and a real evaluation run is computed. Synthetic examples are not research results.

## Recommendation method

The engine currently compares each structured user profile with the seeded career/skill catalogue. Initial configurable factor weights are skills 35%, interests 25%, projects 15%, education 10%, stated career goal 10%, and self-reported experience 5%. These are prototype assumptions, not validated research results. Interest fit uses controlled role-specific mappings; project fit uses exact catalogue skill/tool/industry matches or a catalogue-listed typical-project phrase, not generic shared words. Projects without a specific catalogue match are scored neutrally. Each response contains factor score, configured weight, contribution, evidence, matched skills, missing skills, related projects and input coverage. Unknown information uses a disclosed neutral factor value rather than being reported as negative evidence. Scores are not probabilities of employment.

LLM explanations and coaching receive a structured evidence context, computed ranking, role-catalogue facts and matching curated resource records. The backend uses the project-provided Manus service; the frontend has no LLM credential. When a call cannot produce usable output, the app labels its deterministic evidence-based fallback instead of calling it AI-generated. The role notes are prototype guidance, not universal employer requirements. The eight linked learning resources, their checked date and limitations are recorded in [`rag/learning_resources.json`](rag/learning_resources.json); dated occupational reference mappings and non-direct title caveats are in [catalogue provenance](docs/catalog-provenance.md).

## Resume review and data handling

PDF and DOCX files are size/type/signature checked, parsed in memory and returned as a temporary review draft. A learner can edit, remove, accept or reject extracted fields, including experience-section text excerpts. Those excerpts remain unverified source text and never set an experience-level rating. The raw document is not persisted by default; only accepted structured fields and limited filename/extraction metadata are stored. Temporary review drafts expire after 15 minutes.

## API overview

FastAPI OpenAPI is available at `/docs` and `/openapi.json`. Main APIs include:

- `POST /api/auth/register`, `/login`, `/logout`, `/forgot-password`, `/reset-password`; `GET /api/auth/me`
- `GET/PUT /api/profile`; `POST /api/profile/sample`
- `GET/POST /api/interests`; `POST /api/resume/upload`, `/api/resume/accept`
- `POST /api/career/analyze`; `GET /api/career/recommendations`, `/api/career/catalog`, `/api/career/{id}`, `/api/career/{id}/explanation`
- `GET /api/skills/gaps`; `POST /api/roadmap/generate`; `PUT /api/roadmap/progress`
- `POST /api/ai/chat`, owner-scoped `GET/DELETE /api/ai/history`; researcher-only `GET/POST /api/research/evaluations` and `PUT /api/settings/scoring`; `GET /api/settings`; `GET /api/healthz`

See [API reference](docs/api.md), [local setup](docs/setup.md), and [deployment guide](docs/deployment.md) for request semantics, CSRF, environment configuration and container operation.

## Research and evaluation

See the [26-section research outline](docs/research-outline.md), [verified five-source literature review](docs/literature-review.md), [dated career-catalog provenance and limitations](docs/catalog-provenance.md), [architecture and method](docs/architecture.md), and [database schema](database/schema.md). An authorized evaluation request contains cases of the form below. Every case needs a ground-truth career label and a non-empty ranked prediction list for all four methods. The API computes macro precision/recall/F1 and top-3 accuracy from that actual submitted set and records the case count and dataset name. Optional satisfaction, explanation-usefulness and response-time means are computed only from submitted measurements, with counts; missing measurements are not zero-filled.

```json
{
  "dataset_name": "Reviewed labeled test cohort — version/date",
  "cases": [
    {
      "label": "data-analyst",
      "predictions": {
        "baseline": ["data-analyst", "business-analyst"],
        "ml": ["data-analyst", "data-scientist"],
        "ml_llm": ["data-analyst", "data-scientist"],
        "ml_rag_llm": ["data-analyst", "business-analyst"]
      }
    }
  ]
}
```

That record is an **API shape illustration**, not an evaluation result or empirical result. Do not submit it as real research data.

This build runs the deterministic, configurable weighted recommendation engine and LLM explanation/coach layer. It does not include a trained machine-learning recommender, representative labeled training dataset, or prediction executors for the four evaluation strategies. The researcher API compares predictions generated by actual external or future in-project experiments; it does not train/infer those strategies. With no real study dataset supplied, the research panel intentionally starts with no result metrics. See [ML status and data prerequisites](ml/README.md).

The API integration checks use a temporary SQLite database and do not touch the managed project database:

```bash
python tests/test_api.py
```

## Production notes

Build the frontend with `npm --prefix frontend ci && npm --prefix frontend run build`; build and run the container with the root `Dockerfile`. Provide the managed database and project service environment at runtime. For production HTTPS, leave cookie defaults secure and configure the verified deployed origin as `PUBLIC_APP_URL` before enabling password reset. Protect researcher allowlist and SMTP settings as server-side environment values. No credentials belong in the repository. Publication is a separate step from Preview/checkpoint development.

## Added evidence features (October 2026)

The existing CareerInsight AI architecture now includes two authenticated workspace modules:

- **Skill assessment** (`/api/skill-assessment/*`): a configurable skill catalogue, randomized skill-specific multiple-choice question sets, server-side answer keys, deterministic scoring, feedback/explanations, ownership-checked attempt history, and persisted results. Question banks currently cover the listed programming, web, database, analytics and AI/ML/CS skills. The assessment UI explicitly states that arbitrary code execution is not enabled; no student code is run on the API server.
- **GitHub project analysis** (`/api/github/*`): validates public repository URLs, retrieves repository metadata, language statistics, the recursive file tree, README excerpt and latest commit through the official GitHub API, identifies potential language evidence and basic quality signals, and stores a private per-user report. It does not execute repository code and explicitly warns that file presence/ownership does not prove authorship or proficiency.
- New sidebar navigation items: **Skill assessment** and **GitHub project analysis**.
- New Alembic migration: `0004_evidence_features` creates `skill_assessment_attempts` and `repository_analyses`.

### Database migration

From the repository root, with the virtual environment activated and `DATABASE_URL` configured:

```powershell
alembic upgrade head
```

For local development, `.env.example` documents the available environment variables. Keep real secrets in a local `.env` file; do not commit it. The application can also create tables in local development when `CAREERINSIGHT_AUTO_CREATE=true`, but Alembic migrations are the recommended schema-update path.

### Windows setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend
npm ci
npm run dev
```

The frontend dev script starts both the FastAPI API and Vite. Use the URL printed by Vite (normally `http://localhost:3000`). Public GitHub analysis requires internet access from the backend and is subject to GitHub API rate limits. No GitHub token is required for public repositories. Private repositories and OAuth are not implemented.

### Current limitations

- Skill assessments use curated multiple-choice banks; secure sandboxed coding exercises, hidden code test cases, and LLM-generated questions are not enabled yet. The UI does not pretend code has executed.
- Repository quality checks are lightweight static observations based on public file paths, language stats, and README content. They are not a full security audit, test coverage calculation, or proof of contribution.
- Assessment and repository evidence are persisted separately from self-reported profile skills; this update does not silently overwrite self-reported levels or replace the existing career scoring algorithm.


## Windows local startup (fixed ZIP)

For a fresh local SQLite database, `backend/main.py` now creates any missing tables before seeding the career catalogue. The Windows development launcher configures session/CSRF cookies for local HTTP, so sign-in can work when opening Vite through `localhost` or a LAN IP.

1. Extract the ZIP to a normal folder.
2. Open Command Prompt in the extracted folder.
3. Install backend dependencies once: `python -m pip install -r requirements.txt`
4. Install frontend dependencies once: `cd frontend` then `npm install`
5. Return to the project root and double-click `RUN_CareerInsightAI_Windows.bat` (or run it from Command Prompt).
6. Open `http://localhost:3000/`. Use **Create an account** first if this local database has no account yet, then sign in with that account.

The local launcher is for development only; production must use HTTPS and secure cookies. Existing database files are not deleted.
