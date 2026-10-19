# Deployment guide

## Production container

The root `Dockerfile` builds the pinned React/TypeScript frontend, installs the Python requirements, copies the FastAPI application and frontend output, runs `alembic upgrade head`, then starts Uvicorn on `0.0.0.0:${PORT:-3000}`. It exposes port 3000. The unauthenticated readiness endpoint is `GET /api/healthz` and returns a small JSON status.

For a manual image build:

```bash
docker build -t careerinsight-ai .
docker run --rm -p 3000:3000 --env-file .env careerinsight-ai
```

Supply a managed database connection at runtime; do not bake secrets into the Docker build or frontend bundle. The application normalizes the Webdev `DATABASE_URL` SSL option for PyMySQL while retaining its certificate-verification intent. The database URL is a runtime secret.

## Manus Webdev

The initialized project has the Server and Database capabilities enabled. The platform supplies the managed MySQL-compatible `DATABASE_URL` and the built-in AI service variables. The application uses the managed database for development and publication; they share the same project database. Apply Alembic migrations before local or managed-development startup; startup seeds catalogue defaults but does not create the latest model schema by default. `CAREERINSIGHT_AUTO_CREATE=true` is an opt-in for a disposable database only and must not be combined with a pending Alembic chain. The published container keeps auto-creation disabled and first runs `alembic upgrade head`.

For the published container configuration, set the health path to `/api/healthz` and let the platform provide `PORT` (default 3000). FastAPI serves the compiled SPA and the API from the same published listener. Keep browser-facing API calls relative (`/api/...`). Do not add a separate static catch-all ahead of API routes.

The build can be reproduced with:

```bash
npm --prefix frontend ci
npm --prefix frontend run build
python -m compileall backend
```

## Production configuration

- Leave cookie defaults secure: `Secure; SameSite=None` supports the public HTTPS Preview iframe. Do not set `COOKIE_SECURE=false` outside plain-HTTP local development.
- Configure password-reset email only after SMTP credentials and the verified public origin are set (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS`, `PUBLIC_APP_URL`). Reset responses never include tokens.
- Put the researcher email allowlist in `RESEARCH_ADMIN_EMAILS`; never let a public form choose the account role.
- Keep all secrets server-side. The optional LLM runs through the project-provided Manus API, not a browser key.
- Use additive migrations for schema changes. Development and publication share the managed database, so preview-time data/schema updates are not isolated from the published app.

## Preview and publication

Preview, checkpointing and publication are separate. This delivery is a working Preview. Publish only through the project workflow when publication is explicitly requested; successful local build or Preview health does not mean the app has been published.
