from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CareerRole, CareerSkill, Profile, Project, ScoringSetting, UserInterest, UserSkill
from ..seed import INTERESTS, WEIGHTS

LEVEL = {"not_started": 0, "beginner": 1, "intermediate": 2, "advanced": 3}
LABELS = {"skills": "Skill Match", "interests": "Interest Match", "projects": "Project Match", "education": "Education Match", "goal": "Career Goal Match", "experience": "Experience Match"}
ROLE_INTEREST_MATCHES = {
    "data-analyst": {"working with data", "business analysis", "research"},
    "data-scientist": {"working with data", "developing ai systems", "research", "problem solving"},
    "machine-learning-engineer": {"developing ai systems", "building software", "cloud systems", "research", "problem solving"},
    "ai-engineer": {"developing ai systems", "building software", "product design", "research", "problem solving"},
    "data-engineer": {"working with data", "building software", "cloud systems", "problem solving"},
    "software-developer": {"building software", "product design", "problem solving", "communication"},
    "full-stack-developer": {"building software", "product design", "problem solving", "communication"},
    "cybersecurity-analyst": {"cybersecurity", "research", "problem solving", "communication"},
    "cloud-engineer": {"cloud systems", "building software", "problem solving", "communication"},
    "business-analyst": {"business analysis", "working with data", "communication", "problem solving"},
}

# These are intentionally explicit field aliases, not a broad shared-keyword test.
EDUCATION_FIELDS = {
    "computer science": ("computer science", "computer engineering", "software engineering", "software development"),
    "statistics": ("statistics", "statistical science"),
    "mathematics": ("mathematics", "mathematical sciences", "math"),
    "data science": ("data science", "data analytics"),
    "business": ("business administration", "business", "economics", "commerce", "management"),
    "information systems": ("information technology", "information systems", "information security", "cybersecurity", "network security", "cloud computing"),
    "engineering": ("engineering", "engineering technology"),
}

ROLE_ALIASES = {
    "data-analyst": ("data analyst", "business intelligence analyst", "bi analyst"),
    "data-scientist": ("data scientist", "applied scientist"),
    "machine-learning-engineer": ("machine learning engineer", "ml engineer"),
    "ai-engineer": ("ai engineer", "artificial intelligence engineer"),
    "data-engineer": ("data engineer", "analytics engineer"),
    "software-developer": ("software developer", "software engineer"),
    "full-stack-developer": ("full stack developer", "fullstack developer"),
    "cybersecurity-analyst": ("cybersecurity analyst", "information security analyst", "security analyst"),
    "cloud-engineer": ("cloud engineer", "cloud infrastructure engineer"),
    "business-analyst": ("business analyst", "business systems analyst"),
}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _education_alignment(profile: Profile, role: CareerRole) -> tuple[int, str]:
    provided = " ".join(part for part in (profile.degree, profile.branch, profile.education) if part)
    if not provided.strip():
        return 50, "Education not provided; neutral score used"
    user_text = f" {_normalize(provided)} "
    requirement = f" {_normalize(role.education or '')} "
    matched_field = next(
        (field for field, aliases in EDUCATION_FIELDS.items()
         if any(f" {_normalize(alias)} " in requirement for alias in aliases)
         and any(f" {_normalize(alias)} " in user_text for alias in aliases)),
        None,
    )
    summary = (profile.degree or profile.branch or profile.education).strip()
    if matched_field:
        return 100, f"Education provided: {summary}; aligns with the role's stated education guidance ({matched_field})"
    return 50, f"Education provided: {summary}; no direct catalogue-field match established, so neutral score used"


def _goal_alignment(target: str, role: CareerRole) -> tuple[int, str]:
    if not target or not target.strip():
        return 50, "No user-stated target role; neutral score used"
    target_options = [part.strip() for part in re.split(r"[,;/]|\bor\b|\band\b", target, flags=re.IGNORECASE) if part.strip()]
    supported = {_normalize(role.name), _normalize(role.slug.replace("-", " "))}
    supported.update(_normalize(alias) for alias in ROLE_ALIASES.get(role.slug, ()))
    match = any(_normalize(option) in supported for option in target_options)
    if match:
        return 100, f"User-stated target role exactly matches the catalogue role or a controlled alias: {target.strip()}"
    return 50, f"User-stated target role: {target.strip()}; no exact catalogue role or controlled alias match, so neutral score used"


def _project_catalogue_evidence(project: Project, role: CareerRole, required: list[CareerSkill]) -> list[str]:
    skill_names = {_normalize(item.skill.name) for item in required}
    tool_names = {_normalize(value) for value in (role.tools or [])}
    industry_names = {_normalize(value) for value in (role.industries or [])}
    typical_projects = {_normalize(value) for value in (role.typical_projects or [])}
    evidence = []

    for technology in project.technologies or []:
        key = _normalize(technology)
        if key and key in skill_names:
            evidence.append(f"catalogue skill match: {technology}")
        elif key and key in tool_names:
            evidence.append(f"catalogue tool match: {technology}")

    domain = _normalize(project.domain)
    if domain and domain in industry_names:
        evidence.append(f"catalogue industry match: {project.domain}")

    project_text = f" {_normalize(project.name)} {_normalize(project.description)} "
    for phrase in typical_projects:
        if phrase and f" {phrase} " in project_text:
            evidence.append(f"catalogue project-type match: {phrase}")
    return evidence


def evaluate_role(db: Session, user_id: int, profile: Profile, role: CareerRole, weights: dict | None = None) -> dict:
    weights = weights or WEIGHTS
    required = db.scalars(select(CareerSkill).where(CareerSkill.career_id == role.id)).all()
    current = {row.skill.name.casefold(): row.level for row in db.scalars(select(UserSkill).where(UserSkill.user_id == user_id)).all()}
    explicit_interests = [row.interest.name for row in db.scalars(select(UserInterest).where(UserInterest.user_id == user_id, UserInterest.source == "user")).all()]
    projects = db.scalars(select(Project).where(Project.user_id == user_id)).all()
    matched, missing, skill_evidence, skill_progress = [], [], [], []
    numerator, denominator = 0.0, 0.0
    for req in required:
        name, level = req.skill.name, current.get(req.skill.name.casefold())
        required_rank = max(1, LEVEL.get(req.required_level, 2))
        ratio = min(1.0, LEVEL.get(level or "not_started", 0) / required_rank)
        importance = max(.1, float(req.importance)) * (1.0 if req.required else .65)
        denominator += importance
        numerator += ratio * importance
        severity = "high" if LEVEL.get(level or "not_started", 0) <= required_rank - 2 else ("medium" if ratio < 1 else "low")
        skill_progress.append({"name": name, "current_level": level or "not_started", "required_level": req.required_level, "score": round(100 * ratio), "severity": severity, "required": req.required})
        if level and ratio >= 1:
            matched.append(name)
            skill_evidence.append(f"{name} — {level} (meets the {req.required_level} role requirement)")
        else:
            missing.append(name)
            if level:
                skill_evidence.append(f"{name} — {level}; role lists {req.required_level}")
    skill_score = round(100 * numerator / denominator) if denominator else 50

    interest_hits, interest_evidence = [], []
    supported_interests = {name.casefold() for name in INTERESTS}
    known_interests = [item for item in explicit_interests if item.casefold() in supported_interests]
    if known_interests:
        role_interests = ROLE_INTEREST_MATCHES.get(role.slug, set())
        interest_hits = [item for item in known_interests if item.casefold() in role_interests]
        interest_score = round(100 * len(interest_hits) / len(known_interests))
        interest_evidence = [f"User-selected interest aligned: {item}" for item in interest_hits]
        if not interest_hits:
            interest_evidence = [f"User-selected interest: {item}" for item in known_interests[:3]] + ["No role-specific interest-catalogue mapping matched"]
        if len(known_interests) < len(explicit_interests):
            interest_evidence.append("Previously stored non-catalogue interest values were excluded from the match score")
    else:
        interest_score = 50
        interest_evidence = ["No supported user-confirmed interest assessment yet; neutral score used"]

    project_hits = []
    for project in projects:
        if _project_catalogue_evidence(project, role, required):
            project_hits.append(project.name)
    if projects:
        if project_hits:
            project_score = min(100, round(100 * len(project_hits) / max(1, min(len(projects), 2))))
            project_evidence = [f"Related project matched an exact role-catalogue skill, tool, industry, or typical-project phrase: {name}" for name in project_hits[:3]]
        else:
            project_score = 50
            project_evidence = ["Projects are recorded; no specific role-catalogue field matched, so a neutral score was used"]
    else:
        project_score, project_evidence = 50, ["No projects provided yet; neutral score used"]

    education_score, education_evidence = _education_alignment(profile, role)
    goal_score, goal_evidence_line = _goal_alignment(profile.target_role, role)
    goal_evidence = [goal_evidence_line]

    if profile.experience_level:
        experience_score = min(100, round(100 * LEVEL.get(profile.experience_level, 1) / max(1, LEVEL.get(role.min_experience, 1))))
        experience_evidence = [f"Self-reported experience: {profile.experience_level}; catalogue expectation: {role.min_experience}"]
    else:
        experience_score, experience_evidence = 50, ["Experience level not provided; neutral score used"]

    values = {"skills": skill_score, "interests": interest_score, "projects": project_score, "education": education_score, "goal": goal_score, "experience": experience_score}
    total_weight = sum(float(weights.get(key, 0)) for key in values) or 100.0
    score = round(sum(values[key] * float(weights.get(key, 0)) for key in values) / total_weight)
    factor_evidence = {"skills": skill_evidence, "interests": interest_evidence, "projects": project_evidence, "education": education_evidence, "goal": goal_evidence, "experience": experience_evidence}
    factors = [{"key": key, "label": LABELS[key], "weight": round(100 * float(weights.get(key, 0)) / total_weight), "score": values[key], "contribution": round(values[key] * float(weights.get(key, 0)) / total_weight, 1), "evidence": factor_evidence[key]} for key in values]
    known = sum(bool(getattr(profile, attr, None)) for attr in ["education", "experience_level", "target_role"]) + bool(explicit_interests) + bool(projects) + bool(current)
    coverage = round(100 * known / 6)
    readiness = round(skill_score * .65 + experience_score * .2 + min(100, len(projects) * 25) * .15)
    gaps = [{"name": item["name"], "current": item["current_level"], "required": item["required_level"], "severity": item["severity"]} for item in skill_progress if item["score"] < 100]
    return {"career_id": role.id, "slug": role.slug, "career": role.name, "score": score, "factors": factors, "evidence": [line for group in factor_evidence.values() for line in group], "matched_skills": matched, "missing_skills": missing, "relevant_projects": project_hits, "skill_progress": skill_progress, "readiness": readiness, "coverage": coverage, "_skill_gaps": gaps}


def recommendations(db: Session, user_id: int, profile: Profile) -> list[dict]:
    setting = db.scalar(select(ScoringSetting).where(ScoringSetting.name == "default"))
    weights = setting.weights if setting else WEIGHTS
    roles = db.scalars(select(CareerRole)).all()
    return sorted([evaluate_role(db, user_id, profile, role, weights) for role in roles], key=lambda row: (row["score"], row["readiness"]), reverse=True)
