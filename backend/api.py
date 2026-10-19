from __future__ import annotations
import asyncio, hashlib, os, secrets, smtplib
from datetime import timedelta
from email.message import EmailMessage
from urllib.parse import quote
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import CareerRole, CareerSkill, ChatMessage, EvaluationRun, Interest, PasswordReset, Profile, Project, Recommendation, Resume, Roadmap, ScoringSetting, Skill, SkillGap, User, UserInterest, UserSession, UserSkill, now_utc
from .schemas import ChatIn, EvaluationIn, ForgotPasswordIn, InterestsIn, LoginIn, ProfileIn, RegisterIn, ResetPasswordIn, RoadmapIn, RoadmapProgressIn, ResumeAcceptIn
from .security import COOKIE_NAME, CSRF_NAME, clear_session_cookies, current_user, enforce_rate_limit, hash_password, issue_session, require_csrf, verify_password
from .seed import INTERESTS, WEIGHTS, ensure_catalog
from .services.ai import coach, explain
from .services.evaluation import evaluate_and_store, list_runs
from .services.recommendations import serialize_result
from .services.resume import consume_draft, peek_draft, review_upload
from .services.roadmap import create_roadmap, serialize as serialize_roadmap, update_progress
from .services.resources import resources_for_query
from .services.scoring import recommendations

router = APIRouter(prefix="/api")


def _safe_user(user: User) -> dict:
    profile = user.profile
    complete = bool(profile and profile.education and profile.degree and profile.branch and user.profile and profile.onboarding_complete)
    return {"id":user.id,"name":user.name,"email":user.email,"role":user.role,"profile_complete":complete}


def _csrf_pair(request: Request) -> None:
    cookie = request.cookies.get(CSRF_NAME, "")
    header = request.headers.get("X-CSRF-Token", "")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise HTTPException(403, "Security check failed. Refresh the page and try again.")


def _identity(request: Request, db: Session) -> tuple[User, UserSession]:
    return current_user(request, db)


def _authed_mutation(request: Request, db: Session) -> tuple[User, UserSession]:
    user, session = _identity(request, db)
    require_csrf(request, session)
    return user, session


def _serialize_profile(db: Session, user: User) -> dict:
    profile = user.profile
    skills = db.scalars(select(UserSkill).where(UserSkill.user_id == user.id)).all()
    projects = db.scalars(select(Project).where(Project.user_id == user.id)).all()
    interests = db.scalars(select(UserInterest).where(UserInterest.user_id == user.id)).all()
    return {"name":user.name,"email":user.email,"education":profile.education if profile else "","degree":profile.degree if profile else "","branch":profile.branch if profile else "","graduation_year":profile.graduation_year if profile else None,"experience_level":profile.experience_level if profile else None,"target_role":profile.target_role if profile else "","preferred_industry":profile.preferred_industry if profile else "","skills":[{"name":row.skill.name,"level":row.level,"category":row.skill.category} for row in skills],"soft_skills":(profile.soft_skills or []) if profile else [],"projects":[{"id":row.id,"name":row.name,"description":row.description,"technologies":row.technologies or [],"domain":row.domain} for row in projects],"certifications":list(profile.certifications or []) if profile else [],"interests":[{"name":row.interest.name,"source":row.source,"score":round(row.score*100)} for row in interests]}


def _save_profile(db: Session, user: User, values: dict) -> dict:
    profile = user.profile or Profile(user_id=user.id)
    if user.profile is None: db.add(profile)
    for key in ["education","degree","branch","graduation_year","experience_level","target_role","preferred_industry","soft_skills","certifications"]:
        if key in values: setattr(profile, key, values[key])
    if "skills" in values:
        db.query(UserSkill).filter(UserSkill.user_id == user.id).delete(synchronize_session=False)
        normalized = {}
        for item in values["skills"]:
            name = str(item.get("name", "")).strip()[:100]
            if not name: continue
            level = item.get("level", "beginner")
            if level not in {"beginner","intermediate","advanced"}: level = "beginner"
            normalized[name.casefold()] = (name, level)
        for name in values.get("soft_skills", []):
            name = str(name).strip()[:100]
            if name: normalized.setdefault(name.casefold(), (name,"intermediate"))
        for name, level in normalized.values():
            skill = db.scalar(select(Skill).where(Skill.name.ilike(name)))
            if skill is None: skill = Skill(name=name, category="soft" if name.casefold() in {"communication","leadership","problem solving","teamwork"} else "technical"); db.add(skill); db.flush()
            db.add(UserSkill(user_id=user.id, skill_id=skill.id, level=level, source="user"))
    if "projects" in values:
        db.query(Project).filter(Project.user_id == user.id).delete(synchronize_session=False)
        for item in values["projects"]:
            name = str(item.get("name", "")).strip()[:160]
            if name: db.add(Project(user_id=user.id, name=name, description=str(item.get("description", ""))[:3000], technologies=[str(t)[:80] for t in (item.get("technologies") or [])[:30]], domain=str(item.get("domain", ""))[:100]))
    profile.onboarding_complete = bool(profile.education and profile.degree and profile.branch and (values.get("skills") or values.get("interests") or db.query(UserSkill).filter(UserSkill.user_id == user.id).count()))
    db.commit(); db.refresh(profile)
    return _serialize_profile(db, user)


def _latest_role_result(db: Session, user: User) -> list[dict]:
    if user.profile is None: return []
    return recommendations(db, user.id, user.profile)


def _report_rows(db: Session, user: User, rows: list[dict]) -> None:
    if not rows: return
    for row in rows[:8]:
        dbrow = Recommendation(user_id=user.id, career_id=row["career_id"], score=row["score"], factors={f["key"]:f for f in row["factors"]}, evidence={"items":row["evidence"],"matched_skills":row["matched_skills"],"missing_skills":row["missing_skills"],"relevant_projects":row["relevant_projects"]}, readiness=row["readiness"], coverage=row["coverage"])
        db.add(dbrow); db.flush()
        for gap in row["_skill_gaps"]:
            skill = db.scalar(select(Skill).where(Skill.name == gap["name"]))
            if skill: db.add(SkillGap(recommendation_id=dbrow.id, skill_id=skill.id, current_level=gap["current"], required_level=gap["required"], severity=gap["severity"]))
    db.commit()


@router.get("/healthz")
def health():
    return {"ok":True,"service":"careerinsight-api"}


@router.get("/auth/me")
def auth_me(request: Request, response: Response, db: Session = Depends(get_db)):
    user, session = None, None
    try: user, session = _identity(request, db)
    except HTTPException: pass
    csrf = request.cookies.get(CSRF_NAME, "")
    invalid_session = bool(session and (not csrf or not secrets.compare_digest(hashlib.sha256(csrf.encode()).hexdigest(), session.csrf_hash)))
    if invalid_session:
        clear_session_cookies(response)
        user, session = None, None
    if invalid_session or not csrf:
        from .security import issue_csrf_cookie
        issue_csrf_cookie(response)
    return {"user":_safe_user(user) if user else None}


@router.post("/auth/register")
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    _csrf_pair(request)
    email = str(payload.email).strip().lower()
    enforce_rate_limit(request,"register",email,5,900)
    if db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "An account with this email already exists.")
    allowlist = {x.strip().lower() for x in os.getenv("RESEARCH_ADMIN_EMAILS", "").split(",") if x.strip()}
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role="researcher" if email in allowlist else "learner")
    db.add(user); db.flush()
    db.add(Profile(user_id=user.id, education=payload.education, degree=payload.degree, branch=payload.branch, graduation_year=payload.graduation_year))
    db.commit(); db.refresh(user); issue_session(db,response,user)
    return {"user":_safe_user(user)}


@router.post("/auth/login")
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    _csrf_pair(request)
    email = str(payload.email).strip().lower()
    enforce_rate_limit(request,"login",email,8,900)
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.password_hash): raise HTTPException(401, "Email or password is incorrect.")
    issue_session(db,response,user,payload.remember)
    return {"user":_safe_user(user)}


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    user, session = _authed_mutation(request,db)
    session.revoked_at = now_utc(); db.commit(); clear_session_cookies(response)
    return {"ok":True}


def _send_reset_email(to: str, link: str) -> None:
    host = os.getenv("SMTP_HOST", "").strip(); user = os.getenv("SMTP_USER", ""); password = os.getenv("SMTP_PASSWORD", "")
    from_address = os.getenv("SMTP_FROM", "").strip(); port = int(os.getenv("SMTP_PORT", "587")); starttls = os.getenv("SMTP_STARTTLS", "true").lower() in {"1","true","yes"}
    if not (host and from_address): raise RuntimeError("SMTP is not configured")
    message = EmailMessage(); message["Subject"] = "Reset your CareerInsight AI password"; message["From"] = from_address; message["To"] = to
    message.set_content(f"Use this one-time link within 30 minutes to reset your password:\n\n{link}\n\nIf you did not request this, you can ignore this message.")
    with smtplib.SMTP(host, port, timeout=12) as server:
        if starttls: server.starttls()
        if user: server.login(user,password)
        server.send_message(message)


@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    _csrf_pair(request)
    email = str(payload.email).strip().lower()
    enforce_rate_limit(request,"forgot-password",email,3,3600)
    host = os.getenv("SMTP_HOST", "").strip(); sender = os.getenv("SMTP_FROM", "").strip(); public_url = os.getenv("PUBLIC_APP_URL", "").strip().rstrip("/")
    user = db.scalar(select(User).where(User.email == email))
    if user and host and sender and public_url:
        token = secrets.token_urlsafe(36)
        db.add(PasswordReset(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=now_utc()+timedelta(minutes=30)))
        db.commit()
        try:
            await asyncio.to_thread(_send_reset_email,user.email,public_url+"/?reset="+quote(token))
        except Exception:
            db.query(PasswordReset).filter(PasswordReset.token_hash == hashlib.sha256(token.encode()).hexdigest()).delete(); db.commit()
    message = "If the account exists, password-reset instructions will be sent when email delivery is configured."
    if not (host and sender and public_url): message += " SMTP delivery is not configured in this environment."
    return {"message":message}


@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordIn, request: Request, db: Session = Depends(get_db)):
    _csrf_pair(request)
    enforce_rate_limit(request,"reset-password",hashlib.sha256(payload.token.encode()).hexdigest(),5,3600)
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    reset = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == token_hash, PasswordReset.used_at.is_(None)))
    if not reset or reset.expires_at < now_utc(): raise HTTPException(400,"This reset link is invalid or has expired.")
    user = db.get(User,reset.user_id)
    if not user: raise HTTPException(400,"This reset link is invalid or has expired.")
    user.password_hash = hash_password(payload.password); reset.used_at = now_utc()
    db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).update({"revoked_at":now_utc()},synchronize_session=False)
    db.commit()
    return {"message":"Password reset. Please sign in with your new password."}


@router.get("/profile")
def get_profile(request: Request, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    return _serialize_profile(db,user)


@router.put("/profile")
def put_profile(payload: ProfileIn, request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    return _save_profile(db,user,payload.model_dump())


@router.post("/profile/sample")
def sample_profile(request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    sample = {"education":"Bachelor's degree","degree":"B.Sc. Computer Science","branch":"Computer Science","graduation_year":2026,"experience_level":"intermediate","target_role":"Data Scientist","preferred_industry":"Analytics and technology","skills":[{"name":"Python","level":"advanced"},{"name":"SQL","level":"intermediate"},{"name":"Machine Learning","level":"intermediate"},{"name":"Data Visualization","level":"intermediate"},{"name":"Statistics","level":"beginner"},{"name":"Communication","level":"intermediate"}],"soft_skills":["Communication","Problem Solving"],"projects":[{"name":"Customer churn analysis","description":"Explored customer activity, evaluated baseline models and summarized limitations.","technologies":["Python","SQL","Machine Learning"],"domain":"Data analytics"}],"certifications":[{"name":"Data analysis foundations","platform":"CareerInsight sample data","year":2025}]}
    result = _save_profile(db,user,sample)
    interest_rows = db.scalars(select(Interest).where(Interest.name.in_(["Working with data","Research","Developing AI systems"]))).all()
    db.query(UserInterest).filter(UserInterest.user_id == user.id).delete(synchronize_session=False)
    for row in interest_rows: db.add(UserInterest(user_id=user.id,interest_id=row.id,source="user",score=1.0))
    db.commit()
    return {"profile":_serialize_profile(db,user),"sample_profile":True}


@router.get("/interests")
def get_interests(request: Request, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    selected = db.scalars(select(UserInterest).where(UserInterest.user_id == user.id)).all()
    return {"available":INTERESTS,"selected":[{"name":row.interest.name,"source":row.source,"score":round(row.score*100)} for row in selected]}


@router.post("/interests")
def save_interests(payload: InterestsIn, request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    canonical = {name.casefold(): name for name in INTERESTS}
    submitted = [str(value).strip() for value in payload.interests if str(value).strip()]
    if len(submitted) > len(INTERESTS) or any(len(value) > 100 for value in submitted):
        raise HTTPException(422, "Choose at most the available assessment interests.")
    unknown = [value for value in submitted if value.casefold() not in canonical]
    if unknown:
        raise HTTPException(422, "Choose interests from the provided assessment catalogue.")
    names = list(dict.fromkeys(canonical[value.casefold()] for value in submitted))
    rows = []
    for name in names:
        row = db.scalar(select(Interest).where(Interest.name == name))
        if row is None:
            raise HTTPException(503, "The interest catalogue is temporarily unavailable.")
        rows.append(row)
    db.query(UserInterest).filter(UserInterest.user_id == user.id, UserInterest.source == "user").delete(synchronize_session=False)
    for row in rows:
        db.add(UserInterest(user_id=user.id,interest_id=row.id,source="user",score=1.0))
    db.commit()
    return get_interests(request,db)


@router.post("/resume/upload")
async def upload_resume(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user_id = _authed_mutation(request, db)[0].id
    enforce_rate_limit(request,"resume-upload",str(user_id),5,3600)
    max_mb = max(1,min(20,int(os.getenv("UPLOAD_MAX_MB","8"))))
    return await review_upload(file,user_id,max_mb)


@router.post("/resume/accept")
def accept_resume(payload: ResumeAcceptIn, request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    extracted, filename = peek_draft(payload.draft_id,user.id)
    review_fields = {"skills", "education", "projects", "certifications", "experience_excerpts"}
    accepted = {field: payload.extracted.get(field, []) for field in review_fields}
    accepted["review_note"] = extracted.get("review_note", "")
    for field in review_fields:
        values = accepted.get(field, [])
        if not isinstance(values, list) or len(values) > 30 or any(not isinstance(value, str) for value in values):
            raise HTTPException(422, f"Reviewed resume field '{field}' must be a list of text values.")
        accepted[field] = list(dict.fromkeys(value.strip()[:500] for value in values if value.strip()))
    consume_draft(payload.draft_id,user.id)
    existing = _serialize_profile(db,user)
    if not existing["education"] and accepted.get("education"):
        existing["education"] = accepted["education"][0][:120]
    for skill in accepted.get("skills",[]):
        if not any(s["name"].casefold() == str(skill).casefold() for s in existing["skills"]): existing["skills"].append({"name":str(skill)[:100],"level":"beginner"})
    for project in accepted.get("projects",[]):
        if isinstance(project,str) and project.strip(): existing["projects"].append({"name":"Resume project","description":project[:350],"technologies":[],"domain":""})
    for certification in accepted.get("certifications",[]):
        if isinstance(certification,str) and certification.strip(): existing["certifications"].append({"name":certification[:200],"platform":"Resume extraction","year":None})
    _save_profile(db,user,existing)
    db.add(Resume(user_id=user.id,filename=filename,extracted=accepted)); db.commit()
    return {"ok":True,"message":"Reviewed information was added to your profile."}


@router.get("/career/catalog")
def career_catalog(db: Session = Depends(get_db)):
    rows = db.scalars(select(CareerRole).order_by(CareerRole.name)).all()
    return {"careers":[{"id":r.id,"slug":r.slug,"name":r.name,"description":r.description,"required_skills":[x.skill.name for x in db.scalars(select(CareerSkill).where(CareerSkill.career_id == r.id, CareerSkill.required.is_(True))).all()],"education":r.education,"tools":r.tools,"typical_projects":r.typical_projects} for r in rows]}


@router.post("/career/analyze")
def analyze(request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    if user.profile is None: raise HTTPException(400,"Complete your profile before running career analysis.")
    rows = recommendations(db,user.id,user.profile)
    _report_rows(db,user,rows)
    if rows: create_roadmap(db,user.id,rows[0]["career_id"])
    return {"recommendations":[serialize_result(row) for row in rows]}


@router.get("/career/recommendations")
def get_recommendations(request: Request, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    return {"recommendations":[serialize_result(row) for row in _latest_role_result(db,user)]}


@router.get("/career/{career_id}/explanation")
async def career_explanation(career_id: int, request: Request, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    if user.profile is None: raise HTTPException(404,"Profile not found.")
    row = next((r for r in recommendations(db,user.id,user.profile) if r["career_id"] == career_id),None)
    if row is None: raise HTTPException(404,"Career role not found.")
    return await explain(row)


@router.get("/career/{career_id}")
def career_detail(career_id: int, request: Request, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    role = db.get(CareerRole,career_id)
    if not role: raise HTTPException(404,"Career role not found.")
    result = next((r for r in recommendations(db,user.id,user.profile) if r["career_id"] == career_id),None) if user.profile else None
    return {"id":role.id,"slug":role.slug,"name":role.name,"description":role.description,"education":role.education,"tools":role.tools,"typical_projects":role.typical_projects,"recommendation":serialize_result(result) if result else None}


@router.get("/skills/gaps")
def skill_gaps(request: Request, career_id: int | None = None, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    if not user.profile: return {"career":None,"gaps":[]}
    rows = recommendations(db,user.id,user.profile)
    selected = next((row for row in rows if career_id and row["career_id"] == career_id), rows[0] if rows else None)
    if not selected: return {"career":None,"gaps":[]}
    return {"career":selected["career"],"career_id":selected["career_id"],"gaps":[{"skill":g["name"],"current_level":g["current"],"required_level":g["required"],"gap":g["severity"]} for g in selected["_skill_gaps"]],"matched_skills":selected["matched_skills"]}


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    profile = user.profile
    if not profile:
        return {"profile":_serialize_profile(db,user),"recommendations":[],"roadmap":None,"stats":{"career_match":0,"skill_match":0,"readiness":0,"skill_gaps":0},"catalog_size":db.query(CareerRole).count()}
    rows = _latest_role_result(db,user)
    public_rows = [serialize_result(row) for row in rows]
    top = rows[0] if rows else None
    road = db.scalar(select(Roadmap).where(Roadmap.user_id == user.id).order_by(Roadmap.updated_at.desc()))
    return {"profile":_serialize_profile(db,user),"recommendations":public_rows,"roadmap":serialize_roadmap(road) if road else None,"stats":{"career_match":top["score"] if top else 0,"skill_match":next((f["score"] for f in top["factors"] if f["key"]=="skills"),0) if top else 0,"readiness":top["readiness"] if top else 0,"skill_gaps":len(top["_skill_gaps"]) if top else 0},"catalog_size":db.query(CareerRole).count()}


@router.post("/roadmap/generate")
def generate_roadmap(payload: RoadmapIn, request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    return create_roadmap(db,user.id,payload.career_id)


@router.put("/roadmap/progress")
def progress(payload: RoadmapProgressIn, request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    return update_progress(db,user.id,payload.item_id,payload.status)


@router.post("/ai/chat")
async def chat(payload: ChatIn, request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    enforce_rate_limit(request,"ai-chat",str(user.id),25,60)
    rows = _latest_role_result(db,user)
    top = rows[0] if rows else {}
    alternatives = [{"career":row.get("career"),"score":row.get("score"),"matched_skills":row.get("matched_skills",[]),"missing_skills":row.get("missing_skills",[]),"relevant_projects":row.get("relevant_projects",[])} for row in rows[1:2]]
    saved_roadmap = db.scalar(select(Roadmap).where(Roadmap.user_id == user.id).order_by(Roadmap.updated_at.desc()))
    profile = user.profile
    prior_rows = db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.id.desc()).limit(6)).all()
    history = [{"role":row.role,"content":row.content[:2000]} for row in reversed(prior_rows)]
    user_skills = db.scalars(select(UserSkill).where(UserSkill.user_id == user.id)).all()
    user_interests = db.scalars(select(UserInterest).where(UserInterest.user_id == user.id, UserInterest.source == "user")).all()
    projects = db.scalars(select(Project).where(Project.user_id == user.id)).all()
    role_catalogue = []
    for row in rows[:2]:
        role = db.get(CareerRole, row.get("career_id")) if row.get("career_id") else None
        if not role:
            continue
        requirements = db.scalars(select(CareerSkill).where(CareerSkill.career_id == role.id)).all()
        role_catalogue.append({"career":role.name,"description":role.description,"education_guidance":role.education,"skill_requirements":[{"name":item.skill.name,"required_level":item.required_level,"required":item.required} for item in requirements],"tools":role.tools or [],"industries":role.industries or [],"typical_projects":role.typical_projects or [],"experience_guidance":role.min_experience})
    candidate_skills = list(top.get("missing_skills", [])) + [skill.skill.name for skill in user_skills]
    for alternative in alternatives:
        candidate_skills.extend(alternative.get("missing_skills", []))
    learning_resources = resources_for_query(payload.message, candidate_skills, 4)
    context = {"profile":{"education":profile.education if profile else "","degree":profile.degree if profile else "","field":profile.branch if profile else "","experience_level":profile.experience_level if profile else None,"target_role":profile.target_role if profile else "","preferred_industry":profile.preferred_industry if profile else "","skills":[{"name":item.skill.name,"level":item.level} for item in user_skills],"soft_skills":(profile.soft_skills or []) if profile else [],"user_stated_interests":[item.interest.name for item in user_interests],"projects":[{"name":item.name,"description":item.description,"technologies":item.technologies or [],"domain":item.domain} for item in projects],"certifications":list(profile.certifications or []) if profile else []},"career":top.get("career"),"score":top.get("score"),"matched_skills":top.get("matched_skills",[]),"missing_skills":top.get("missing_skills",[]),"relevant_projects":top.get("relevant_projects",[]),"evidence":top.get("evidence",[]),"alternatives":alternatives,"career_catalogue":role_catalogue,"roadmap":serialize_roadmap(saved_roadmap) if saved_roadmap else None,"prior_chat_history":history,"learning_resources":learning_resources}
    db.add(ChatMessage(user_id=user.id,role="user",content=payload.message[:2000])); db.commit()
    answer = await coach(payload.message,context)
    db.add(ChatMessage(user_id=user.id,role="assistant",content=answer["reply"][:3000],ai_generated=answer["ai_generated"],resources=answer.get("resources",[]))); db.commit()
    return answer


@router.get("/ai/history")
def chat_history(request: Request, db: Session = Depends(get_db)):
    user, _ = _identity(request, db)
    messages = db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.id.desc()).limit(40)).all()
    return {"messages":[{"id":row.id,"role":row.role,"content":row.content,"ai_generated":row.ai_generated,"resources":row.resources or [],"created_at":row.created_at} for row in reversed(messages)]}


@router.delete("/ai/history")
def clear_chat_history(request: Request, db: Session = Depends(get_db)):
    user, _ = _authed_mutation(request, db)
    deleted = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    return {"ok":True,"deleted":deleted}


@router.get("/research/evaluations")
def research_evaluations(request: Request, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    if user.role not in {"researcher","admin"}: raise HTTPException(403,"Research evaluation is available only to authorized users.")
    runs = list_runs(db)
    return {"authorized":True,"runs":runs,"message":None if runs else "No evaluation runs have been recorded. Metrics will appear only after an evaluation on labeled test data."}


@router.post("/research/evaluations")
def run_research(payload: EvaluationIn, request: Request, db: Session = Depends(get_db)):
    user,_ = _authed_mutation(request,db)
    if user.role not in {"researcher","admin"}: raise HTTPException(403,"Research evaluation is available only to authorized users.")
    enforce_rate_limit(request,"research-evaluation",str(user.id),5,3600)
    catalogue = db.scalars(select(CareerRole)).all()
    canonical = {}
    for role in catalogue:
        canonical[" ".join(role.name.casefold().split())] = role.slug
        canonical[" ".join(role.slug.replace("-", " ").casefold().split())] = role.slug
    def canonical_label(value: str) -> str:
        key = " ".join(value.replace("-", " ").replace("_", " ").casefold().split())
        if key not in canonical:
            raise HTTPException(422,"Evaluation labels and predictions must use career roles in the catalogue.")
        return canonical[key]
    cases = []
    for item in payload.cases:
        case = item.model_dump(exclude_none=True)
        case["label"] = canonical_label(case["label"])
        case["predictions"] = {method:[canonical_label(candidate) for candidate in values] for method,values in case["predictions"].items()}
        cases.append(case)
    return {"authorized":True,"runs":evaluate_and_store(db,cases,payload.dataset_name)}


@router.get("/settings")
def settings(request: Request, db: Session = Depends(get_db)):
    user,_ = _identity(request,db)
    row = db.scalar(select(ScoringSetting).where(ScoringSetting.name == "default"))
    return {"email":user.email,"role":user.role,"scoring_weights":row.weights if row else WEIGHTS,"weights_note":"Initial configurable prototype assumptions; not scientifically validated."}


@router.put("/settings/scoring")
def update_scoring(payload: dict, request: Request, db: Session = Depends(get_db)):
    user, _ = _authed_mutation(request, db)
    if user.role not in {"researcher", "admin"}:
        raise HTTPException(403, "Scoring weights can be changed only by an authorized researcher.")
    weights = payload.get("weights")
    if not isinstance(weights, dict) or set(weights) != set(WEIGHTS):
        raise HTTPException(422, "Provide all six scoring factor weights.")
    try: normalized = {key: float(value) for key, value in weights.items()}
    except (TypeError, ValueError): raise HTTPException(422, "Weights must be numeric values.")
    if any(value < 0 or value > 100 for value in normalized.values()) or round(sum(normalized.values())) != 100:
        raise HTTPException(422, "Weights must be between 0 and 100 and sum to 100.")
    setting = db.scalar(select(ScoringSetting).where(ScoringSetting.name == "default"))
    if setting is None:
        setting = ScoringSetting(name="default", weights=normalized, version=1); db.add(setting)
    else:
        setting.weights = normalized; setting.version += 1
    db.commit()
    return {"weights": normalized, "version": setting.version, "note": "Configurable project settings; not scientifically validated."}

# Evidence-based skill assessments and public GitHub repository inspection.
import random as _random
import re as _re
import httpx as _httpx
from .models import SkillAssessmentAttempt, RepositoryAnalysis

_SKILL_BANK = {
    "Python": [
        {"id":"py1","type":"mcq","difficulty":"beginner","prompt":"Coding question: What is the output of this Python code?\nnums = [1, 2, 3]\nprint([n * n for n in nums])","options":["[1, 4, 9]","[1, 2, 3]","[2, 3, 4]","An error occurs"],"answer":0,"explanation":"A list comprehension uses square brackets and an expression followed by for."},
        {"id":"py2","type":"mcq","difficulty":"intermediate","prompt":"Code-reading question: What does len({1, 1, 2, 3}) return?","options":["4","3","2","Error"],"answer":1,"explanation":"A set stores unique values, so the duplicate 1 is stored once."},
        {"id":"py3","type":"mcq","difficulty":"intermediate","prompt":"Which construct is best for reliably closing a file after reading?","options":["try only","with open(...) as file","global file","del open"],"answer":1,"explanation":"The with statement uses a context manager to close the file when the block ends."},
        {"id":"py4","type":"mcq","difficulty":"advanced","prompt":"Average-case lookup in a Python dictionary is typically what time complexity?","options":["O(n)","O(log n)","O(1)","O(n log n)"],"answer":2,"explanation":"Hash-table lookup is typically constant time on average, though worst cases can differ."}
    ],
    "SQL": [
        {"id":"sql1","type":"mcq","difficulty":"beginner","prompt":"SQL code question: In SELECT * FROM students WHERE marks > 80 GROUP BY branch, which clause filters rows before grouping?","options":["HAVING","WHERE","ORDER BY","GROUP BY"],"answer":1,"explanation":"WHERE filters input rows before aggregation."},
        {"id":"sql2","type":"mcq","difficulty":"intermediate","prompt":"Which join returns only rows with matching keys in both tables?","options":["LEFT JOIN","FULL JOIN","INNER JOIN","CROSS JOIN"],"answer":2,"explanation":"INNER JOIN returns matching rows from both sides."},
        {"id":"sql3","type":"mcq","difficulty":"intermediate","prompt":"Which expression counts distinct customer IDs?","options":["COUNT(customer_id)","COUNT(DISTINCT customer_id)","SUM(DISTINCT customer_id)","UNIQUE(customer_id)"],"answer":1,"explanation":"COUNT(DISTINCT column) counts unique non-NULL values."},
        {"id":"sql4","type":"mcq","difficulty":"advanced","prompt":"Which clause filters groups after aggregate calculations?","options":["WHERE","HAVING","LIMIT","FROM"],"answer":1,"explanation":"HAVING filters grouped results, often using aggregate expressions."}
    ],
    "JavaScript": [
        {"id":"js1","type":"mcq","difficulty":"beginner","prompt":"Which keyword declares a block-scoped variable that can be reassigned?","options":["const","let","static","define"],"answer":1,"explanation":"let declares a block-scoped binding that can be reassigned."},
        {"id":"js2","type":"mcq","difficulty":"intermediate","prompt":"What does Array.map() return?","options":["The original array only","A new array of mapped results","A number","Always a Promise"],"answer":1,"explanation":"map creates a new array from each element's callback result."},
        {"id":"js3","type":"mcq","difficulty":"intermediate","prompt":"Which operator checks both value and type equality?","options":["==","=","===","!==="],"answer":2,"explanation":"The strict equality operator === compares without type coercion."},
        {"id":"js4","type":"mcq","difficulty":"advanced","prompt":"An async function always returns what?","options":["A string","A Promise","An array","A callback"],"answer":1,"explanation":"An async function returns a Promise, even when its body returns a plain value."}
    ],
    "Machine Learning": [
        {"id":"ml1","type":"mcq","difficulty":"beginner","prompt":"Why split data into training and test sets?","options":["To increase rows","To estimate performance on unseen data","To remove all missing values","To guarantee 100% accuracy"],"answer":1,"explanation":"The test set helps estimate generalization to data not used for fitting."},
        {"id":"ml2","type":"mcq","difficulty":"intermediate","prompt":"Which is a common sign of overfitting?","options":["Poor train and test scores","Excellent train score but much worse test score","Identical train and test sets","No model parameters"],"answer":1,"explanation":"Overfit models learn training-specific patterns that do not generalize well."},
        {"id":"ml3","type":"mcq","difficulty":"intermediate","prompt":"Which technique is appropriate for scaling features using training-set statistics?","options":["Fit scaler on all data before splitting","Fit scaler on training data, then transform test data","Scale the target labels randomly","Never scale any feature"],"answer":1,"explanation":"Fitting preprocessing only on training data prevents test-set leakage."},
        {"id":"ml4","type":"mcq","difficulty":"advanced","prompt":"For a highly imbalanced binary classifier, which metric can be more informative than accuracy alone?","options":["File size","Precision/recall or PR-AUC","Number of columns only","Training duration only"],"answer":1,"explanation":"Precision-recall metrics reveal minority-class performance better than accuracy alone."}
    ]
}

_SKILL_CATALOG = [
    {"name":"Python","category":"Programming","description":"Python syntax, data structures and practical problem solving."},
    {"name":"Java","category":"Programming","description":"Object-oriented programming and Java language fundamentals."},
    {"name":"C","category":"Programming","description":"C language basics, pointers and memory concepts."},
    {"name":"C++","category":"Programming","description":"C++ fundamentals, STL and object-oriented programming."},
    {"name":"JavaScript","category":"Web Development","description":"JavaScript language and browser programming fundamentals."},
    {"name":"HTML","category":"Web Development","description":"Semantic markup and accessible page structure."},
    {"name":"CSS","category":"Web Development","description":"Layouts, selectors and responsive styling."},
    {"name":"React","category":"Web Development","description":"Components, props, state and UI composition."},
    {"name":"SQL","category":"Databases","description":"Filtering, joins, grouping and relational queries."},
    {"name":"MySQL","category":"Databases","description":"Relational database operations and query design."},
    {"name":"Excel","category":"Data Analytics","description":"Formulas, data cleanup and spreadsheet analysis."},
    {"name":"Power BI","category":"Data Analytics","description":"Data modelling, visuals and reporting."},
    {"name":"Pandas","category":"Data Analytics","description":"Tabular data transformation and analysis."},
    {"name":"NumPy","category":"Data Analytics","description":"Array operations and numerical computing."},
    {"name":"Machine Learning","category":"AI and Machine Learning","description":"Model evaluation, preprocessing and algorithm selection."},
    {"name":"Deep Learning","category":"AI and Machine Learning","description":"Neural network concepts and model training."},
    {"name":"Data Structures and Algorithms","category":"Computer Science","description":"Core data structures and algorithmic reasoning."},
    {"name":"Object-Oriented Programming","category":"Computer Science","description":"Classes, encapsulation, inheritance and polymorphism."},
    {"name":"DBMS","category":"Computer Science","description":"Relational modelling, transactions and database fundamentals."},
    {"name":"Statistics","category":"Data Science","description":"Probability, distributions, hypothesis testing and statistical interpretation."},
    {"name":"Git and GitHub","category":"Developer Tools","description":"Version control, commits, branches, pull requests and repository collaboration."},
    {"name":"Data Science","category":"AI and Data Science","description":"Data cleaning, exploratory analysis, visualization and communicating insights."},
    {"name":"Microsoft Word","category":"Productivity","description":"Document formatting, styles, tables and professional document workflows."},
    {"name":"Communication","category":"Professional Skills","description":"Clear professional communication and collaboration fundamentals."}
]

# Curated, deterministic baseline questions for the remaining catalogue skills.
_EXTRA_BANKS = {
 "Java": [("Which keyword creates a subclass?",["extends","implements","package","import"],0,"extends defines class inheritance."),("Which collection rejects duplicate elements?",["ArrayList","HashSet","LinkedList","Vector"],1,"A Set stores unique elements.")],
 "C": [("Which symbol obtains the address of a variable?",["*","&","%","#"],1,"The unary & operator returns an object's address."),("Which header declares printf?",["stdlib.h","string.h","stdio.h","math.h"],2,"printf is declared in stdio.h.")],
 "C++": [("Which feature lets a function share a name with different parameter lists?",["Overloading","Casting","Looping","Linking"],0,"Function overloading uses the same name with different parameter lists."),("Which STL container stores key-value pairs with unique keys?",["vector","stack","map","queue"],2,"std::map stores unique keys mapped to values.")],
 "HTML": [("Which element is most appropriate for a page's main content?",["<main>","<span>","<b>","<small>"],0,"The main element identifies the dominant page content."),("Which attribute provides alternative text for an image?",["title","alt","srcset","role"],1,"alt text communicates image meaning when it cannot be seen.")],
 "CSS": [("Which CSS layout system is designed for one-dimensional rows or columns?",["Grid","Flexbox","Float only","Position fixed"],1,"Flexbox is designed primarily for one-dimensional layout."),("Which selector targets an element with id=header?",[".header","#header","header*","@header"],1,"The # prefix selects an ID." )],
 "React": [("What is a React prop used for?",["Passing data to a component","Creating a database","Starting a server","Replacing HTML"],0,"Props pass data from a parent component to a child."),("Which hook stores component state?",["useRoute","useState","useHTML","useServer"],1,"useState provides state in function components.")],
 "MySQL": [("Which command retrieves rows from a table?",["FETCH TABLE","SELECT","PULL","READ TABLE"],1,"SELECT retrieves data from tables."),("Which constraint uniquely identifies each row?",["DEFAULT","CHECK","PRIMARY KEY","INDEX ONLY"],2,"A primary key uniquely identifies a row.")],
 "Excel": [("Which function adds values that meet a condition?",["COUNTBLANK","SUMIF","LEFT","CONCAT"],1,"SUMIF adds values that satisfy a criterion."),("Which reference stays fixed when copied?",["A1","$A$1","A$","1A"],1,"Absolute references use dollar signs for both column and row.")],
 "Power BI": [("What is DAX primarily used for?",["Data modelling expressions and calculations","Styling web pages","Writing Java classes","Managing Git branches"],0,"DAX defines measures and calculated columns in Power BI models."),("Why define relationships between tables?",["To enable related data filtering and analysis","To change file extensions","To encrypt visuals","To increase image size"],0,"Relationships allow filters and analysis to flow between related tables.")],
 "Pandas": [("Which Pandas object is two-dimensional and labeled?",["Series","DataFrame","ndarray","Tuple"],1,"A DataFrame is a two-dimensional labeled tabular structure."),("Which method quickly summarizes numeric columns?",["describe()","compile()","render()","connect()"],0,"describe provides summary statistics for columns.")],
 "NumPy": [("Which NumPy structure is central to array computing?",["ndarray","DataFrame","Cursor","DOM"],0,"ndarray is NumPy's core N-dimensional array type."),("What does broadcasting enable?",["Operations on compatible differently shaped arrays","Network access","Database backups","HTML rendering"],0,"Broadcasting aligns compatible shapes for elementwise operations.")],
 "Deep Learning": [("What is the role of an activation function?",["Introduce non-linearity","Store training files","Split databases","Replace loss functions"],0,"Activation functions allow neural networks to model nonlinear patterns."),("What does backpropagation compute?",["Gradients for model parameters","Only class names","Dataset filenames","Image dimensions only"],0,"Backpropagation calculates gradients used to update parameters.")],
 "Data Structures and Algorithms": [("Which data structure follows FIFO order?",["Stack","Queue","Tree","Heap"],1,"A queue processes first-in, first-out."),("Binary search on a sorted array has what time complexity?",["O(n)","O(log n)","O(n²)","O(1) always"],1,"Binary search halves the remaining search space each step.")],
 "Object-Oriented Programming": [("Which concept hides internal state behind a public interface?",["Encapsulation","Recursion","Compilation","Iteration"],0,"Encapsulation groups state and behavior while controlling access."),("Polymorphism allows what?",["One interface with multiple implementations","Only one class per project","Data without types","A program without functions"],0,"Polymorphism lets the same interface behave differently by implementation.")],
 "DBMS": [("Which property means a transaction is all-or-nothing?",["Atomicity","Consistency","Isolation","Durability"],0,"Atomicity prevents a transaction from being partially applied."),("What is database normalization intended to reduce?",["Redundancy and update anomalies","All relationships","Every query","All constraints"],0,"Normalization structures data to reduce duplication and anomalies.")],
 "Statistics": [("What does the median represent?",["The middle value in ordered data","The most frequent value always","The sum of all values","The range only"],0,"The median is the middle value after sorting."),("What does a p-value help assess?",["Compatibility of data with a null hypothesis","Dataset file size","Number of columns","Model deployment speed"],0,"A p-value measures how surprising the data are under a specified null hypothesis.")],
 "Git and GitHub": [("Which command records staged changes in Git history?",["git commit","git status","git clone","git fetch"],0,"git commit creates a commit from staged changes."),("What is a pull request commonly used for?",["Proposing and reviewing changes before merging","Deleting all branches automatically","Installing Python","Creating a local folder only"],0,"Pull requests support code review and discussion before merging changes.")],
 "Data Science": [("What is the main purpose of exploratory data analysis?",["Understand patterns, distributions and data quality","Guarantee perfect predictions","Replace all testing","Encrypt a dataset"],0,"EDA helps understand structure, patterns, outliers and data quality."),("Why should test data be kept separate during model development?",["To estimate performance on unseen data","To make training scores larger","To remove the target column forever","To increase duplicate rows"],0,"Held-out test data provides a less biased estimate of generalization.")],
 "Microsoft Word": [("What is the benefit of using heading styles?",["Consistent formatting and document navigation","Automatic internet access","Encrypting every file by default","Creating database tables"],0,"Heading styles improve consistency and support navigation and accessibility."),("Which feature is best for arranging information in rows and columns in a document?",["Table","WordArt only","Page color","Find and replace"],0,"Tables organize information into rows and columns.")],
 "Communication": [("Which is a good practice in professional communication?",["Be clear, respectful and specific","Use vague requests only","Ignore the audience","Avoid confirming next steps"],0,"Clear and respectful messages make requests and expectations easier to understand."),("What is active listening?",["Paying attention and confirming understanding","Interrupting frequently","Preparing a reply without listening","Changing the topic"],0,"Active listening includes attention, clarification and checking understanding.")]
}
for _skill, _items in _EXTRA_BANKS.items():
    _SKILL_BANK[_skill] = [{"id":f"{_skill.lower().replace(' ','').replace('/','')}{i+1}","type":"mcq","difficulty":"beginner" if i == 0 else "intermediate","prompt":q,"options":opts,"answer":answer,"explanation":explanation} for i,(q,opts,answer,explanation) in enumerate(_items)]

@router.get("/skill-assessment/catalog")
def skill_assessment_catalog(request: Request, db: Session = Depends(get_db)):
    user, _ = _identity(request, db)
    latest = {}
    rows = db.scalars(select(SkillAssessmentAttempt).where(SkillAssessmentAttempt.user_id == user.id).order_by(SkillAssessmentAttempt.created_at.desc())).all()
    for row in rows:
        latest.setdefault(row.skill_name.casefold(), {"score":row.score,"level":row.level,"created_at":row.created_at.isoformat()})
    return {"skills":[{**skill,"previous":latest.get(skill["name"].casefold())} for skill in _SKILL_CATALOG],"assessment_supported":sorted(_SKILL_BANK.keys())}

@router.post("/skill-assessment/start")
def skill_assessment_start(payload: dict, request: Request, db: Session = Depends(get_db)):
    user, _ = _authed_mutation(request, db)
    name = str(payload.get("skill", "")).strip()
    canonical = next((s["name"] for s in _SKILL_CATALOG if s["name"].casefold() == name.casefold()), None)
    bank = _SKILL_BANK.get(canonical or "")
    if not canonical or not bank:
        raise HTTPException(422, "No assessment question bank is available for that skill yet.")
    requested_level = str(payload.get("level", "beginner")).strip().casefold()
    level_aliases = {"medium": "intermediate", "high": "advanced"}
    requested_level = level_aliases.get(requested_level, requested_level)
    if requested_level not in {"beginner", "intermediate", "advanced"}:
        raise HTTPException(422, "Choose beginner, intermediate, or advanced level.")
    level_bank = [q for q in bank if q.get("difficulty", "beginner") == requested_level]
    if not level_bank:
        # Keep every catalogue skill usable at each selected stage; clearly label the requested stage.
        level_bank = bank
    selected = _random.sample(level_bank, min(4, len(level_bank)))
    # Persist the stage the learner requested, so a perfect beginner quiz is not
    # incorrectly reported as advanced. Difficulty is evidence-bounded.
    selected = [{**q, "_requested_stage": requested_level} for q in selected]
    public_questions = [{k:v for k,v in q.items() if k not in {"answer","explanation","_requested_stage"}} for q in selected]
    attempt = SkillAssessmentAttempt(user_id=user.id, skill_name=canonical, questions=selected, answers={}, score=0, level="in_progress", attempted=0, total=len(selected))
    db.add(attempt); db.commit(); db.refresh(attempt)
    return {"attempt_id":attempt.id,"skill":canonical,"questions":public_questions,"total":len(selected),"mode":"multiple_choice","level":requested_level,"note":f"{requested_level.title()} stage. Questions are selected from this level only; code is not executed by the assessment."}

@router.post("/skill-assessment/{attempt_id}/submit")
def skill_assessment_submit(attempt_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    user, _ = _authed_mutation(request, db)
    attempt = db.scalar(select(SkillAssessmentAttempt).where(SkillAssessmentAttempt.id == attempt_id, SkillAssessmentAttempt.user_id == user.id))
    if not attempt: raise HTTPException(404, "Assessment attempt not found.")
    if attempt.level != "in_progress": raise HTTPException(409, "This assessment has already been submitted.")
    answers = payload.get("answers")
    if not isinstance(answers, dict): raise HTTPException(422, "Answers must be provided as an object.")
    questions = attempt.questions or []
    valid_ids = {q["id"] for q in questions}
    if any(key not in valid_ids for key in answers): raise HTTPException(422, "An answer refers to a question outside this assessment.")
    attempted = sum(1 for q in questions if q["id"] in answers)
    correct = sum(1 for q in questions if answers.get(q["id"]) == q["answer"])
    score = round(correct / len(questions) * 100) if questions else 0
    requested_stage = next((q.get("_requested_stage") for q in questions if q.get("_requested_stage")), "beginner")
    # Passing an easier stage demonstrates that stage; it must not automatically
    # promote a learner to a harder stage without completing harder questions.
    if attempted < max(3, len(questions)):
        level = "insufficient_evidence"
    elif score < 40:
        level = "beginner"
    elif requested_stage == "beginner":
        level = "beginner"
    elif requested_stage == "intermediate":
        level = "intermediate" if score >= 60 else "beginner"
    else:
        level = "advanced" if score >= 60 else ("intermediate" if score >= 40 else "beginner")
    attempt.answers = {str(k):v for k,v in answers.items()}; attempt.score=score; attempt.level=level; attempt.attempted=attempted
    # Assessment results update the profile skill level automatically when all questions were answered.
    if level in {"beginner", "intermediate", "advanced"} and attempted == len(questions) and questions:
        skill_row = db.scalar(select(Skill).where(Skill.name.ilike(attempt.skill_name)))
        if skill_row is None:
            skill_row = Skill(name=attempt.skill_name, category="assessed"); db.add(skill_row); db.flush()
        user_skill = db.scalar(select(UserSkill).where(UserSkill.user_id == user.id, UserSkill.skill_id == skill_row.id))
        if user_skill is None:
            user_skill = UserSkill(user_id=user.id, skill_id=skill_row.id, level=level, source="assessment"); db.add(user_skill)
        else:
            user_skill.level = level
            user_skill.source = "assessment"
    db.commit()
    feedback = [{"id":q["id"],"prompt":q["prompt"],"correct":answers.get(q["id"]) == q["answer"],"explanation":q["explanation"],"correct_option":q["answer"]} for q in questions]
    return {"attempt_id":attempt.id,"skill":attempt.skill_name,"score":score,"level":level,"attempted":attempted,"total":len(questions),"correct":correct,"feedback":feedback,"recommendation":"Insufficient evidence: complete all questions for a level estimate." if level=="insufficient_evidence" else ("Review the explanations and try another assessment." if score<80 else "Try a more advanced practical exercise next." )}

@router.get("/skill-assessment/history")
def skill_assessment_history(request: Request, db: Session = Depends(get_db)):
    user, _ = _identity(request, db)
    rows = db.scalars(select(SkillAssessmentAttempt).where(SkillAssessmentAttempt.user_id == user.id).order_by(SkillAssessmentAttempt.created_at.desc()).limit(100)).all()
    return {"attempts":[{"id":r.id,"skill":r.skill_name,"score":r.score,"level":r.level,"attempted":r.attempted,"total":r.total,"created_at":r.created_at.isoformat()} for r in rows]}

@router.post("/github/analyze")
async def github_analyze(payload: dict, request: Request, db: Session = Depends(get_db)):
    user, _ = _authed_mutation(request, db)
    raw = str(payload.get("url", "")).strip()
    # Accept copied GitHub URLs that include tracking query strings or fragments.
    raw = raw.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    match = _re.fullmatch(r"https?://(?:www\.)?github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9_.-]{1,100})", raw, flags=_re.IGNORECASE)
    if not match: raise HTTPException(422, "Enter a public GitHub repository URL such as https://github.com/owner/repository.")
    owner, repo = match.group(1), match.group(2).removesuffix(".git")
    headers = {"Accept":"application/vnd.github+json", "User-Agent":"CareerInsightAI-Repository-Analyzer", "X-GitHub-Api-Version":"2022-11-28"}
    async with _httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        response = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
        if response.status_code == 404: raise HTTPException(404, "Repository not found or not publicly accessible.")
        if response.status_code == 403: raise HTTPException(429, "GitHub API rate limit or access restriction reached. Please try again later.")
        if response.status_code >= 400: raise HTTPException(502, "GitHub could not provide repository metadata right now.")
        metadata = response.json()
        if metadata.get("private"): raise HTTPException(422, "Only public repositories are supported. No private repository data was accessed.")
        branch = metadata.get("default_branch") or "main"
        contents_response = await client.get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{quote(branch, safe='')}?recursive=1", headers=headers)
        tree = contents_response.json().get("tree", []) if contents_response.status_code == 200 else []
        paths = [item.get("path","") for item in tree if item.get("type")=="blob"]
        readme_response = await client.get(f"https://api.github.com/repos/{owner}/{repo}/readme", headers=headers)
        readme_text = ""
        if readme_response.status_code == 200:
            try:
                import base64 as _base64
                readme_text = _base64.b64decode(readme_response.json().get("content", "")).decode("utf-8", "replace")[:12000]
            except Exception: readme_text = ""
        language_response = await client.get(f"https://api.github.com/repos/{owner}/{repo}/languages", headers=headers)
        languages = language_response.json() if language_response.status_code == 200 else {}
        commits_response = await client.get(f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1", headers=headers)
        latest_commit = None
        if commits_response.status_code == 200 and commits_response.json(): latest_commit = commits_response.json()[0].get("commit",{}).get("author",{}).get("date")
    extensions = {p.rsplit(".",1)[-1].lower() for p in paths if "." in p and not p.startswith(".")}
    detected = []
    checks = [("Python", {"py"}), ("JavaScript", {"js","jsx","mjs","cjs"}), ("TypeScript", {"ts","tsx"}), ("Java", {"java"}), ("C/C++", {"c","cc","cpp","h","hpp"}), ("HTML/CSS", {"html","css","scss"}), ("SQL", {"sql"}), ("Jupyter/Pandas", {"ipynb"})]
    for skill, exts in checks:
        if extensions & exts: detected.append({"skill":skill,"evidence":"File extensions found in public repository tree: " + ", ".join(sorted(exts & extensions)),"confidence":"medium","limitation":"File presence suggests use; it does not prove authorship or proficiency."})
    flags = {"readme_present":any(p.lower() in {"readme.md","readme.rst","readme.txt"} for p in paths),"tests_present":any("test" in p.lower() or "spec" in p.lower() for p in paths),"ci_present":any(p.startswith(".github/workflows/") for p in paths),"dependency_files":[p for p in paths if p.split("/")[-1].lower() in {"requirements.txt","pyproject.toml","package.json","pom.xml","cargo.toml","go.mod"}][:20]}
    report = {"repository_url":metadata.get("html_url",raw),"name":metadata.get("full_name",f"{owner}/{repo}"),"description":metadata.get("description"),"stars":metadata.get("stargazers_count",0),"forks":metadata.get("forks_count",0),"languages":languages,"file_count":len(paths),"skills":detected,"quality_observations":flags,"readme_excerpt":readme_text[:2000],"latest_commit_at":latest_commit,"limitations":["Only public GitHub metadata, file paths and README excerpt were inspected.","Repository code was not executed.","Detected files do not prove individual authorship; describe your contribution before using this as a skill claim."]}
    # Save the analyzed repository directly to the user's profile in the backend.
    # This avoids relying on a second frontend request to persist the project.
    project_name = str(report.get("name") or f"{owner}/{repo}")[:160]
    project_description = str(report.get("description") or "")
    if not project_description:
        project_description = f"Analyzed public GitHub repository. {report['file_count']} files detected; languages: {', '.join(report['languages'].keys()) or 'not detected'}. Repository: {report['repository_url']}"
    project = db.scalars(select(Project).where(Project.user_id == user.id, Project.name == project_name)).first()
    if project is None:
        project = Project(user_id=user.id, name=project_name)
        db.add(project)
    project.description = project_description[:3000]
    project.technologies = list(report["languages"].keys())[:30]
    project.domain = "GitHub project"

    # Record detected repository languages as low-confidence evidence only.
    for item in detected:
        skill_name = str(item["skill"])[:100]
        skill = db.scalar(select(Skill).where(Skill.name.ilike(skill_name)))
        if skill is None:
            skill = Skill(name=skill_name, category="technical")
            db.add(skill)
            db.flush()
        user_skill = db.scalars(select(UserSkill).where(UserSkill.user_id == user.id, UserSkill.skill_id == skill.id)).first()
        if user_skill is None:
            db.add(UserSkill(user_id=user.id, skill_id=skill.id, level="beginner", source="github"))

    saved = RepositoryAnalysis(user_id=user.id, repository_url=report["repository_url"], repository_name=report["name"], summary=report)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return {"analysis_id":saved.id, **report, "profile_saved": True, "profile_saved_message": "Repository project details were saved to My Profile. Detected languages are recorded as low-confidence evidence."}

@router.get("/github/history")
def github_history(request: Request, db: Session = Depends(get_db)):
    user, _ = _identity(request, db)
    rows = db.scalars(select(RepositoryAnalysis).where(RepositoryAnalysis.user_id == user.id).order_by(RepositoryAnalysis.created_at.desc()).limit(50)).all()
    return {"analyses":[{"id":r.id,"repository_url":r.repository_url,"repository_name":r.repository_name,"summary":r.summary,"created_at":r.created_at.isoformat()} for r in rows]}
