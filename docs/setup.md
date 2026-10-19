# Local setup

## Prerequisites

- Python 3.12 (3.11 is also suitable for local use), Node.js 22 and npm.
- A terminal at the repository root.

## Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
npm --prefix frontend ci
npm --prefix frontend run dev
```

`npm run dev` starts both the FastAPI development process and Vite; do not also start a second API process on port 8000. Open `http://localhost:3000`. FastAPI docs are at `http://localhost:8000/docs`.

## macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
npm --prefix frontend ci
npm --prefix frontend run dev
```

The combined development command runs FastAPI on `8000` and Vite on `3000`. Use the corresponding local URLs above.

## Environment and data

The application reads `.env` values without overriding values injected by the host environment. Leave `DATABASE_URL` blank for a local SQLite file (`careerinsight.db`); Webdev supplies a managed MySQL `DATABASE_URL`. The setup commands apply the committed Alembic migrations before app startup; schema auto-creation is opt-in and off by default to avoid masking unapplied migrations. Set `COOKIE_SECURE=false` and `COOKIE_SAMESITE=lax` only when visiting the app over plain local HTTP. The shipped `.env.example` contains these local-only cookie values; do not carry them into HTTPS production.

The career catalogue is seeded idempotently on startup after the migrated schema is available. Reapply the committed schema migration chain after pulling schema changes by running:

```bash
python -m alembic upgrade head
```

Never point tests at the managed database. The API integration test creates an isolated temporary SQLite database:

```bash
python tests/test_api.py
```

## Optional capabilities

- The managed Webdev runtime supplies the built-in Manus AI service variables. The app uses them server-side; there is no LLM key in the frontend.
- Password reset remains unavailable until `SMTP_HOST`, `SMTP_FROM` and `PUBLIC_APP_URL` are configured. Additional SMTP settings are documented in `.env.example`; reset tokens are never exposed in API responses.
- `RESEARCH_ADMIN_EMAILS` is a comma-separated server-side allowlist for accounts allowed to view evaluations and change scoring weights.
