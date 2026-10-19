from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(24), default="learner", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    profile: Mapped["Profile | None"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    education: Mapped[str] = mapped_column(String(120), default="")
    degree: Mapped[str] = mapped_column(String(160), default="")
    branch: Mapped[str] = mapped_column(String(160), default="")
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(24), nullable=True, default=None)
    target_role: Mapped[str] = mapped_column(String(160), default="")
    preferred_industry: Mapped[str] = mapped_column(String(160), default="")
    soft_skills: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)
    user: Mapped[User] = relationship(back_populates="profile")


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), default="technical")


class UserSkill(Base):
    __tablename__ = "user_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    level: Mapped[str] = mapped_column(String(24), default="beginner")
    source: Mapped[str] = mapped_column(String(24), default="user")
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)
    skill: Mapped[Skill] = relationship()


class Interest(Base):
    __tablename__ = "interests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), default="career")


class UserInterest(Base):
    __tablename__ = "user_interests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    interest_id: Mapped[int] = mapped_column(ForeignKey("interests.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(24), default="user")
    score: Mapped[float] = mapped_column(Float, default=1.0)
    __table_args__ = (UniqueConstraint("user_id", "interest_id", name="uq_user_interest"),)
    interest: Mapped[Interest] = relationship()


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    domain: Mapped[str] = mapped_column(String(100), default="")


class CareerRole(Base):
    __tablename__ = "career_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text)
    education: Mapped[str] = mapped_column(String(160), default="Related degree or equivalent experience")
    tools: Mapped[list] = mapped_column(JSON, default=list)
    typical_projects: Mapped[list] = mapped_column(JSON, default=list)
    industries: Mapped[list] = mapped_column(JSON, default=list)
    min_experience: Mapped[str] = mapped_column(String(24), default="beginner")


class CareerSkill(Base):
    __tablename__ = "career_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("career_roles.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    importance: Mapped[float] = mapped_column(Float, default=1.0)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    required_level: Mapped[str] = mapped_column(String(24), default="intermediate")
    __table_args__ = (UniqueConstraint("career_id", "skill_id", name="uq_career_skill"),)
    skill: Mapped[Skill] = relationship()


class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("career_roles.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float)
    factors: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    readiness: Mapped[float] = mapped_column(Float, default=0)
    coverage: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    career: Mapped[CareerRole] = relationship()


class SkillGap(Base):
    __tablename__ = "skill_gaps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    current_level: Mapped[str] = mapped_column(String(24), default="not_started")
    required_level: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(24))
    skill: Mapped[Skill] = relationship()


class Roadmap(Base):
    __tablename__ = "roadmaps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("career_roles.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)
    career: Mapped[CareerRole] = relationship()
    items: Mapped[list["RoadmapItem"]] = relationship(back_populates="roadmap", cascade="all, delete-orphan", order_by="RoadmapItem.id")


class RoadmapItem(Base):
    __tablename__ = "roadmap_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.id", ondelete="CASCADE"), index=True)
    phase: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="not_started")
    skill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    roadmap: Mapped[Roadmap] = relationship(back_populates="items")


class ChatMessage(Base):
    __tablename__ = "chat_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    resources: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class ScoringSetting(Base):
    __tablename__ = "scoring_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    weights: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    method: Mapped[str] = mapped_column(String(64))
    dataset_name: Mapped[str] = mapped_column(String(160))
    sample_count: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


Index("ix_recommendation_user_career_created", Recommendation.user_id, Recommendation.career_id, Recommendation.created_at)


class SkillAssessmentAttempt(Base):
    __tablename__ = "skill_assessment_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_name: Mapped[str] = mapped_column(String(100), index=True)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(24), default="insufficient_evidence")
    attempted: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class RepositoryAnalysis(Base):
    __tablename__ = "repository_analyses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    repository_url: Mapped[str] = mapped_column(String(500))
    repository_name: Mapped[str] = mapped_column(String(200))
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
