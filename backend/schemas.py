from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Level = Literal["beginner", "intermediate", "advanced"]
EvaluationMethod = Literal["baseline", "ml", "ml_llm", "ml_rag_llm"]

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)
    education: str = Field(default="", max_length=120)
    degree: str = Field(default="", max_length=160)
    branch: str = Field(default="", max_length=160)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    remember: bool = False

class ProfileIn(BaseModel):
    education: str = Field(default="", max_length=120)
    degree: str = Field(default="", max_length=160)
    branch: str = Field(default="", max_length=160)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    experience_level: Level | None = None
    target_role: str = Field(default="", max_length=160)
    preferred_industry: str = Field(default="", max_length=160)
    skills: list[dict] = Field(default_factory=list, max_length=100)
    soft_skills: list[str] = Field(default_factory=list, max_length=24)
    projects: list[dict] = Field(default_factory=list, max_length=30)
    certifications: list[dict] = Field(default_factory=list, max_length=30)

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, values):
        for item in values:
            if not isinstance(item, dict) or not str(item.get("name", "")).strip() or item.get("level", "beginner") not in ("beginner", "intermediate", "advanced"):
                raise ValueError("Each skill needs a name and a valid beginner/intermediate/advanced level.")
        return values

class InterestsIn(BaseModel):
    interests: list[str] = Field(max_length=30)

class RoadmapIn(BaseModel):
    career_id: int

class RoadmapProgressIn(BaseModel):
    item_id: int
    status: Literal["not_started", "in_progress", "complete"]

class ChatIn(BaseModel):
    message: str = Field(min_length=2, max_length=2000)

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=24, max_length=200)
    password: str = Field(min_length=10, max_length=256)

class ResumeAcceptIn(BaseModel):
    draft_id: str = Field(min_length=20, max_length=100)
    extracted: dict

class EvaluationMeasurementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    satisfaction: float | None = Field(default=None, ge=1, le=5)
    explanation_usefulness: float | None = Field(default=None, ge=1, le=5)
    response_time_ms: float | None = Field(default=None, ge=0, le=86_400_000)

class EvaluationCaseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=160)
    predictions: dict[EvaluationMethod, list[str]]
    measurements: dict[EvaluationMethod, EvaluationMeasurementIn] = Field(default_factory=dict)

    @field_validator("predictions")
    @classmethod
    def require_all_methods(cls, value):
        methods = {"baseline", "ml", "ml_llm", "ml_rag_llm"}
        if set(value) != methods:
            raise ValueError("Predictions must include baseline, ml, ml_llm and ml_rag_llm.")
        if any(not items or len(items) > 100 for items in value.values()):
            raise ValueError("Each ranked prediction list must contain 1 to 100 careers.")
        return value

class EvaluationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_name: str = Field(default="Research evaluation dataset", min_length=1, max_length=160)
    cases: list[EvaluationCaseIn] = Field(min_length=1, max_length=500)

class PublicModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
