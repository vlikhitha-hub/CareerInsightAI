# Curated retrieval scope

`learning_resources.json` is the small, versioned external resource collection used for learning links in personalized roadmaps and the AI coach. The current eight entries were opened and checked on **2026-10-07**. Their title, provider, exact HTTPS URL, matched skill tags, short page-supported description and review date travel with each retrieved link.

Retrieval is deterministic keyword/tag matching, not semantic-vector search. It returns at most four resources from this file and never constructs or guesses a URL. The coach receives those records as untrusted source context and may not invent a citation or link. Roadmap and coach UI links point directly to the listed providers and open in a new tab.

The first-party career-role records (`backend/seed.py`) contain author-created, demonstrative role descriptions, required/preferred skills, experience levels, industries, tools and example projects. They are not labor-market facts or authoritative requirements, and the weighted recommendation assumptions have not been academically validated. `docs/catalog-provenance.md` maps each seeded role to a checked official occupational profile where possible, distinguishing direct titles from broad analogues. A broad analogue is context only and does not validate a CareerInsight skill threshold, recommendation score or user outcome.

Before public/academic release, re-check URLs, titles, revisions, provider access terms and whether each resource remains appropriate and accessible in the user's jurisdiction. The resource list does not imply provider endorsement, a credential, free access in all forms, or employment outcomes.
