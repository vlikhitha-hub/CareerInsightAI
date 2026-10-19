from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models import CareerRole, CareerSkill, Project, Roadmap, RoadmapItem, User, UserInterest, UserSkill, now_utc
from .resources import find_learning_resource
from .scoring import LEVEL

PHASE_ORDER = {"Foundation": 0, "Core Skills": 1, "Projects": 2, "Portfolio": 3, "Career Preparation": 4}


def _build_plan(db: Session, user_id: int, career: CareerRole) -> list[tuple[str, str, str, str | None]]:
    user = db.get(User, user_id)
    profile = user.profile if user else None
    user_skills = db.scalars(select(UserSkill).where(UserSkill.user_id == user_id)).all()
    current = {row.skill.name.casefold(): row for row in user_skills}
    interests = [row.interest.name for row in db.scalars(select(UserInterest).where(UserInterest.user_id == user_id, UserInterest.source == "user")).all()]
    projects = db.scalars(select(Project).where(Project.user_id == user_id)).all()
    project_names = [item.name for item in projects]

    required = db.scalars(select(CareerSkill).where(CareerSkill.career_id == career.id)).all()
    gaps = []
    for item in required:
        found = current.get(item.skill.name.casefold())
        user_level = found.level if found else None
        if LEVEL.get(user_level or "not_started", 0) < LEVEL.get(item.required_level, 2):
            gaps.append(item)
    gaps.sort(key=lambda item: (not item.required, -float(item.importance), item.skill.name.casefold()))

    interest_context = f" Consider connecting the work to your stated interest in {interests[0]}." if interests else " Choose a domain you would personally like to explore; no interest has been assumed."
    project_context = f" Your profile lists existing work: {', '.join(project_names[:2])}. Extend one only if it fits your current goals." if project_names else " Your profile does not list a project yet; start with a small, scoped example."

    def skill_description(skill: str, activity: str) -> str:
        found = current.get(skill.casefold())
        if found:
            return f"Your profile lists {found.level} {skill}. {activity}"
        return f"No self-reported {skill} level appears in your profile. Begin with a small, role-relevant exercise; this is not an assessment of your ability. {activity}"

    plan: list[tuple[str, str, str, str | None]] = []
    for skill, activity in [
        ("Python", f"Review data types, functions and small scripts that support {career.name} work."),
        ("SQL", "Practice filtering, joins and aggregation on a small dataset."),
        ("Statistics", "Review distributions, summary measures and the limits of conclusions from data."),
    ]:
        plan.append(("Foundation", skill, skill_description(skill, activity), skill))

    core = [
        ("Machine Learning", "Study supervised-learning concepts and evaluate one small example; relate it to the role catalogue rather than assuming it is a job requirement."),
        ("Data Visualization", "Create a clear, accessible visual explanation of a problem and the evidence behind it."),
    ]
    added: set[str] = set()
    for title, activity in core:
        plan.append(("Core Skills", title, skill_description(title, activity), title))
        added.add(title.casefold())
    for gap in gaps[:3]:
        name = gap.skill.name
        if name.casefold() in added:
            continue
        found = current.get(name.casefold())
        current_note = f" Your profile lists {found.level} in this skill." if found else " This skill is not self-reported in your profile."
        plan.append(("Core Skills", f"Strengthen {name}", f"The {career.name} catalogue lists {name} at {gap.required_level} level.{current_note} Choose a learning exercise, record evidence of completion and reassess the profile when ready.", name))
        added.add(name.casefold())

    gaps_note = f" Prioritize the current catalogue gaps: {', '.join(item.skill.name for item in gaps[:3])}." if gaps else " Your current profile meets the listed required skill levels; use a project to demonstrate and refresh them."
    plan.extend([
        ("Projects", "Project 1", f"Build a small, reproducible {career.name} project that demonstrates role-relevant skills.{gaps_note}{interest_context}", None),
        ("Projects", "Project 2", f"Extend a project with testing, evaluation and a short explanation of what the evidence does—and does not—support.{project_context}{interest_context}", None),
        ("Portfolio", "GitHub", "Publish selected work with a clear README and reproducible setup; remove secrets and personal information.", "Git"),
        ("Portfolio", "Resume", "Review your resume for accuracy and describe only work you actually completed.", None),
        ("Portfolio", "LinkedIn", "Update the profile with current goals and verified project examples; avoid unsupported claims.", None),
        ("Career Preparation", "Mock Interviews", f"Practice explaining a {career.name} project, your decisions and its limitations.", None),
        ("Career Preparation", "Applications", "Prepare a focused application plan and record applications only when you choose to submit them.", None),
        ("Career Preparation", "Internships", "Explore internship or work-based learning options that match your interests; no outcome is guaranteed.", None),
    ])
    return plan


def serialize(roadmap: Roadmap) -> dict:
    items = sorted(roadmap.items, key=lambda item: (PHASE_ORDER.get(item.phase, 99), item.id))
    return {"id": roadmap.id, "career": roadmap.career.name if roadmap.career else "Career path", "items": [{"id": item.id, "phase": item.phase, "title": item.title, "description": item.description, "status": item.status, "skill": item.skill, "resource": find_learning_resource(item.skill)} for item in items]}


def create_roadmap(db: Session, user_id: int, career_id: int) -> dict:
    career = db.get(CareerRole, career_id)
    if not career:
        raise HTTPException(404, "Career role not found.")
    plan = _build_plan(db, user_id, career)
    roadmap = db.scalar(select(Roadmap).where(Roadmap.user_id == user_id, Roadmap.career_id == career_id).order_by(Roadmap.updated_at.desc()))
    if roadmap is None:
        roadmap = Roadmap(user_id=user_id, career_id=career_id)
        db.add(roadmap)
        db.flush()
    existing_by_key = {(item.phase, item.title): item for item in roadmap.items}
    desired_keys = set()
    for phase, title, description, skill in plan:
        key = (phase, title)
        desired_keys.add(key)
        item = existing_by_key.get(key)
        if item:
            item.description = description
            item.skill = skill
        else:
            db.add(RoadmapItem(roadmap_id=roadmap.id, phase=phase, title=title, description=description, skill=skill, status="not_started"))
    for key, item in existing_by_key.items():
        if key not in desired_keys and item.status == "not_started":
            db.delete(item)
        elif key not in desired_keys:
            item.description = "Retained from an earlier profile-targeted plan so your saved progress is preserved. Reassess this activity against your current goals."
    roadmap.updated_at = now_utc()
    db.commit()
    db.refresh(roadmap)
    return serialize(roadmap)


def update_progress(db: Session, user_id: int, item_id: int, status: str) -> dict:
    item = db.get(RoadmapItem, item_id)
    if not item or not item.roadmap or item.roadmap.user_id != user_id:
        raise HTTPException(404, "Roadmap item not found.")
    item.status = status
    item.roadmap.updated_at = now_utc()
    db.commit()
    return {"ok": True, "item_id": item.id, "status": item.status}
