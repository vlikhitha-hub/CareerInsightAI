# LLM integration

`backend/services/ai.py` uses the project-provided Manus LLM service from the FastAPI server. No provider API key is placed in the React bundle. The recommender's score is computed before explanation; the language model may explain evidence but may not modify scores or invent profile facts, skills, interests, requirements, sources or outcomes.

The explanation and coach prompts treat user-controlled profile, resume and chat strings as untrusted data. Coach context includes the signed-in user's structured profile, computed top recommendations, bounded recent conversation, saved roadmap, matching role-catalogue records and the exact curated resource records returned by `backend/services/resources.py`. Career descriptions and requirements are prototype-authored catalogue guidance, not authoritative universal job rules. External learning links are selected deterministically from `rag/learning_resources.json`; the model is instructed not to create links.

When the model service is unavailable or returns no usable response, the backend emits an explicitly non-AI deterministic evidence summary. Conversation records store the user/assistant messages and resource metadata under the owner account. API setup, methods, authentication, and safety behavior are documented in `docs/api.md` and `docs/architecture.md`.
