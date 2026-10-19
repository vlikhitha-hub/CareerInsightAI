# Database schema overview

The SQLAlchemy models in `backend/models/` are authoritative. The managed database is MySQL-compatible; standalone development defaults to SQLite. `DATABASE_URL` is read at runtime. Alembic migrations are committed under `backend/migrations/`.

| Table | Purpose / ownership |
|---|---|
| `users` | Unique email, password hash, name, server-assigned role and active status. |
| `user_sessions` | Hashed opaque session token, hashed CSRF token, expiry and revocation; owned by a user. |
| `password_resets` | Hashed single-use token, short expiry and consumed timestamp; never returns raw token via API. |
| `profiles` | Unique profile per user: education, nullable experience level (`NULL` means not provided, not Beginner), goal, soft skills and certifications. Migration `0002_nullable_experience_level` preserves this distinction for existing records. |
| `skills` / `user_skills` | Extensible skill catalogue and per-user self-reported level/source. |
| `interests` / `user_interests` | Available interest vocabulary and per-user interest/source/score; current UI saves user-stated interests. |
| `projects` | User-owned project name, description, technologies and domain. |
| `career_roles` / `career_skills` | Structured role requirements, tools, education, example projects, skill importance and level. |
| `resumes` | User-owned accepted extraction JSON and filename metadata; raw documents are not stored by default. |
| `recommendations` / `skill_gaps` | Persisted computed role scores, factor/evidence JSON and role-specific gap rows. |
| `roadmaps` / `roadmap_progress` | User-owned career roadmap and item statuses, persistently updated. |
| `chat_history` | User-scoped coach turns and whether a reply came from the LLM; nullable JSON resource references accompany assistant replies. Migration `0003_chat_message_resources` adds the reference field without overwriting message content. |
| `scoring_settings` | Backend-configurable versioned factor weights. |
| `evaluation_runs` | Actual authorized evaluation dataset name, sample count, computed metrics and timestamp. |

Foreign keys and indexes enforce relational linkage and common lookup paths. All learner profile, project, resume, recommendation, roadmap and conversation lookups must scope to the authenticated `user_id`. Research records are visible only through researcher-authorized endpoints. Migration changes are additive by default; destructive schema changes require a separately reviewed plan.
