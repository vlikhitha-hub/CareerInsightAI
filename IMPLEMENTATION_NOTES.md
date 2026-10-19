# CareerInsight AI update notes

## Implemented
- Added persistent assessment-attempt and public-repository-report models plus Alembic migration `0004_evidence_features`.
- Added authenticated APIs for skill catalogue, randomized assessment start, answer submission/scoring, assessment history, public GitHub repository analysis and per-user analysis history.
- Added skill assessment and GitHub project analysis pages to the existing React app sidebar.
- Assessment answer keys remain server-side; results are deterministic and persisted. Short/incomplete evidence is labeled insufficient rather than over-classified.
- GitHub analysis uses official public API endpoints, validates repository URL shape, handles missing/rate-limited repositories, never executes repository code, and shows authorship/evidence limitations.
- Updated README with setup and limitations.

## Validation performed
- Python source and migration files pass `compileall`/syntax compilation.
- Alembic migration chain successfully advanced to `0004_evidence_features` against a local SQLite database.
- Full pytest collection could not run because this execution environment is missing the project's declared `pwdlib` dependency.
- Frontend build could not be completed because `npm ci` did not finish in this environment and left incomplete `node_modules`; the build reports missing installed type packages. Run `npm ci` in a network-enabled environment, then `npm run build`.

## Important scope boundary
This update does not add a secure sandbox for arbitrary student code, and it does not execute submitted or repository code. Skill checks currently use curated multiple-choice question banks. GitHub quality signals are lightweight observations, not a full code review or security audit. The existing career recommendation/scoring logic is preserved.

## Assessment/profile reliability updates (2026-10-11)
- Assessment result levels are bounded by the stage the learner actually took. A high score on a beginner quiz no longer automatically promotes the profile to advanced; harder-stage evidence is required.
- Practical coding checks now include Python, C, Java, C++, and SQL/DBMS examples. They use lightweight source-pattern checks and do not execute submitted code, so results are practice estimates rather than proof of correctness.
- Public GitHub analysis maps detected repository evidence into profile skills automatically. Repository evidence is a signal, not proof of authorship or mastery.
- LinkedIn certification panel accepts a profile URL and certification details for profile sync. A LinkedIn URL alone cannot expose private uploaded certificates to this app; LinkedIn authentication/API access would be required for genuine automatic import.
- Speech input uses the browser's SpeechRecognition API where supported. Use localhost or HTTPS and allow microphone permission; LAN HTTP origins may be blocked by browsers. Typing a transcript remains the fallback.
