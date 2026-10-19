# API reference

All application endpoints are served by FastAPI under `/api`. The interactive OpenAPI reference is at `/docs`, with the machine-readable schema at `/openapi.json`.

## Session and CSRF handling

- `GET /api/auth/me` returns the current user or `null` and issues an anonymous `csrf_token` cookie if needed. It does not write session data. If a signed-in browser has lost or mismatched its CSRF cookie, the endpoint clears that stale browser session and starts a fresh anonymous CSRF pair; sign in again.
- A signed-in session uses an opaque `career_session` cookie (`HttpOnly`) and a readable `csrf_token` cookie. Mutating requests include the matching `X-CSRF-Token` header.
- Session lifetime is 12 hours by default; `remember: true` requests a 30-day session. Logout revokes the server-side session.
- Public HTTPS uses `Secure; SameSite=None` for embedded Preview compatibility. For local plain HTTP only, set `COOKIE_SECURE=false` and `COOKIE_SAMESITE=lax`.
- JSON validation errors are returned as HTTP 422. Protected routes return 401 when signed out and 403 when authorization or CSRF checks fail.

The browser API client at `frontend/src/api.ts` automatically uses same-origin credentials and the CSRF header. Never place server credentials in browser code.

Sensitive actions have account-keyed sliding-window limits and return HTTP 429 with `Retry-After` when exceeded: registration (5 per email/15 minutes), login (8/email/15 minutes), reset requests (3/email/hour), reset attempts (5/token/hour), resume upload (5/user/hour), AI chat (25/user/minute), and research evaluation (5/researcher/hour). Limits are held in process memory (identity values are hashed); a multi-replica deployment should replace this prototype limiter with a shared rate-limit store.

## Account and profile endpoints

| Method and path | Access | Purpose |
|---|---|---|
| `POST /api/auth/register` | Public + CSRF | Register using name, email, password, education, degree, branch and optional graduation year. Passwords must be at least 10 characters. |
| `POST /api/auth/login` | Public + CSRF | Sign in using email, password and optional `remember`. |
| `POST /api/auth/logout` | Signed-in + CSRF | Revoke the current session. |
| `POST /api/auth/forgot-password` | Public + CSRF | Request reset instructions. The response never contains a reset token; delivery requires SMTP and `PUBLIC_APP_URL`. |
| `POST /api/auth/reset-password` | Public + CSRF | Redeem the one-time emailed token with a new password. |
| `GET /api/profile` | Signed in | Read the current user's profile. |
| `PUT /api/profile` | Signed in + CSRF | Validate and update the current user's education, experience level, goal, skills, soft skills, projects and certifications. Skill levels are `beginner`, `intermediate` or `advanced`. |
| `POST /api/profile/sample` | Signed in + CSRF | Replace the signed-in profile with clearly identified sample profile data for a live demo; recommendations are computed by the real scoring engine. |
| `GET /api/settings` | Signed in | Read the caller's account role and current factor weights. |
| `PUT /api/settings/scoring` | Authorized researcher/admin + CSRF | Update all six backend weights; values must be numeric, within 0–100 and sum to 100. These are prototype assumptions, not validated measures. |

## Interests and resume review

| Method and path | Access | Purpose |
|---|---|---|
| `GET /api/interests` | Signed in | Read selectable interests and the user's saved selections. |
| `POST /api/interests` | Signed in + CSRF | Save only exact selections from the seeded interest assessment catalogue; unknown/user-invented catalogue entries return 422 without clearing existing selections. User selections are never relabeled as AI-inferred preferences. |
| `POST /api/resume/upload` | Signed in + CSRF | Upload a `file` using multipart form data. Only validated PDF/DOCX within the configured size cap is accepted. Returns extracted `education`, `skills`, `projects`, `certifications`, and `experience_excerpts` captured from identified experience sections, plus an in-memory `draft_id`. The excerpts are source text only; no experience level is inferred. |
| `POST /api/resume/accept` | Signed in + CSRF | Submit `{ "draft_id": "…", "extracted": { … } }` after user review/edit. Omitted list fields are treated as intentionally removed; accepted experience excerpts remain reviewed text and never overwrite self-reported seniority. Only accepted structured information is stored; the original document is not persisted by default. Drafts expire after 15 minutes. |

Invalid resume types return 415; files that exceed the limit return 413. If reviewed JSON is malformed, the request is rejected without consuming the draft, allowing the user to correct it.

## Recommendations, evidence and roadmap

| Method and path | Access | Purpose |
|---|---|---|
| `GET /api/career/catalog` | Public catalogue | Read the seeded career catalogue, requirements, education, tools and typical projects. |
| `POST /api/career/analyze` | Signed in + CSRF | Compute and persist ranked recommendations from the structured profile and configured factors. |
| `GET /api/career/recommendations` | Signed in | Read the latest computed recommendations. |
| `GET /api/career/{career_id}` | Signed in | Read a role and its current profile-specific match, if available. |
| `GET /api/career/{career_id}/explanation` | Signed in | Return the evidence-grounded explanation and `ai_generated` flag; a deterministic fallback is explicitly distinguished. |
| `GET /api/skills/gaps?career_id={id}` | Signed in | Read matched skills and role-specific current/required levels and gap severity. Omit `career_id` to use the current top match. |
| `POST /api/roadmap/generate` | Signed in + CSRF | Create a personalized five-phase roadmap for `{ "career_id": 1 }`. |
| `PUT /api/roadmap/progress` | Signed in + CSRF | Update an owned item with status `not_started`, `in_progress` or `complete`. |
| `GET /api/dashboard` | Signed in | Read current profile, backend-computed recommendations, persisted roadmap/progress, summary metrics and career-catalogue count. |

Recommendation response objects include the computed score, the six weighted factor scores/contributions/evidence, coverage, matched/missing skills, skill-progress levels, related projects and readiness. Scores are decision-support outputs, not employment probabilities.

## AI coach and research

- `POST /api/ai/chat` accepts `{ "message": "…" }`, is authenticated and CSRF-protected, and returns `{ "reply": "…", "ai_generated": true|false, "resources": [...] }`. Server-side prompts treat profile strings, current and prior questions, role-catalog fields and notes as untrusted data; context includes current structured profile evidence, the two highest-ranked role-catalog records and matching provider-verified resource records. Role requirements remain prototype guidance, not authoritative universal requirements. If the built-in LLM is unavailable, a safe evidence-based fallback is returned. The selected links are saved with the assistant chat record.
- `GET /api/ai/history` returns up to the latest 40 messages, in chronological order, for the authenticated account only. Each assistant message includes its saved provider-reviewed learning-resource links. `DELETE /api/ai/history` removes only the signed-in user's conversation, requires CSRF, and returns `{ "ok": true, "deleted": n }`; the UI confirms this irreversible user-requested deletion first.
- `GET /api/research/evaluations` and `POST /api/research/evaluations` are restricted server-side to researcher/admin accounts. Public registration cannot choose a privileged role; the server assigns research access only to addresses in `RESEARCH_ADMIN_EMAILS`.
- A POST evaluation body contains a `dataset_name` and labeled `cases`; each case supplies a ground-truth label and ranked predictions for `baseline`, `ml`, `ml_llm` and `ml_rag_llm`. Labels must match a seeded career slug or name. The API calculates macro precision/recall/F1 and top-3 accuracy from the predictions actually submitted; it does not fabricate predictions or train/infer models in the evaluation endpoint. Optional `measurements` are keyed by method, e.g. `{ "ml_llm": { "satisfaction": 4, "explanation_usefulness": 3.5, "response_time_ms": 420 } }`. Ratings must be 1–5, latency must be measured in milliseconds, and each optional result is averaged only over the submitted measurements; its sample count is stored alongside the mean. Omitted measurements remain absent, never zero or estimated. No rows/metrics are shown when no run exists.

The ten initial catalogue entries are not empirical research observations. Do not submit synthetic examples as test data or present resulting example metrics as real-world findings.
