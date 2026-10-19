from __future__ import annotations
import io, re, secrets, time
from docx import Document
from pypdf import PdfReader
from fastapi import HTTPException, UploadFile

DRAFTS: dict[str, tuple[int, dict, float, str]] = {}
SKILL_TERMS = ["Python", "SQL", "Machine Learning", "Statistics", "Data Visualization", "Excel", "Power BI", "Tableau", "React", "TypeScript", "JavaScript", "FastAPI", "Cloud", "Docker", "Cybersecurity", "Linux", "Networking", "Git", "Databases", "Communication", "Problem Solving"]

def _extract_text(data: bytes, suffix: str) -> str:
    try:
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages[:20])
        doc = Document(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)[:120_000]
    except Exception as exc:
        raise HTTPException(400, "This document could not be read. Please upload a valid PDF or DOCX.") from exc

def _experience_excerpts(text: str) -> list[str]:
    lines = [line.strip().lstrip("•*- ").strip() for line in text.splitlines() if line.strip()]
    experience_heading = re.compile(r"^\s*(?:(?:professional|work)\s+)?(?:experience|employment(?:\s+history)?|work\s+history|internships?)\s*:?\s*(.*)$", re.I)
    other_heading = re.compile(r"^\s*(?:education|academic background|skills?|technical skills|projects?|certifications?|summary|profile|awards|languages|interests|references)\s*:?\s*$", re.I)
    in_experience = False
    excerpts = []
    for line in lines:
        match = experience_heading.match(line)
        if match:
            in_experience = True
            if match.group(1).strip():
                excerpts.append(match.group(1).strip()[:500])
            continue
        if other_heading.match(line):
            in_experience = False
            continue
        if in_experience or re.search(r"\b(?:worked\s+(?:as|at)|employed\s+(?:as|by)|internship\s+at|employment\s+at)\b", line, re.I):
            excerpts.append(line[:500])
        if len(excerpts) >= 10:
            break
    return list(dict.fromkeys(excerpts))

async def review_upload(upload: UploadFile, user_id: int, max_mb: int) -> dict:
    filename = upload.filename or "resume"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(415, "Upload a PDF or DOCX resume.")
    content_type = (upload.content_type or "").split(";", 1)[0].strip().casefold()
    allowed_types = {
        ".pdf": {"application/pdf", "application/x-pdf", "application/octet-stream"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip", "application/octet-stream"},
    }
    if content_type not in allowed_types[suffix]:
        raise HTTPException(415, "The resume file type does not match a supported PDF or DOCX upload.")
    data = await upload.read(max_mb * 1024 * 1024 + 1)
    if not data or len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Resume must be smaller than {max_mb} MB.")
    if suffix == ".pdf" and not data.startswith(b"%PDF"):
        raise HTTPException(400, "The selected file does not appear to be a valid PDF.")
    if suffix == ".docx" and not data.startswith(b"PK"):
        raise HTTPException(400, "The selected file does not appear to be a valid DOCX document.")
    text = _extract_text(data, suffix)[:120_000]
    low = text.casefold()
    skills = [term for term in SKILL_TERMS if term.casefold() in low]
    projects = []
    for block in re.split(r"\n\s*\n", text):
        if re.search(r"\b(project|developed|built|implemented)\b", block, re.I) and len(block.strip()) > 25:
            projects.append(block.strip()[:350])
        if len(projects) == 4: break
    education_lines = [line.strip()[:240] for line in text.splitlines() if re.search(r"\b(university|college|bachelor|master|degree|B\.Sc|M\.Sc|B\.Tech|M\.Tech|BCA|MCA)\b", line, re.I)][:5]
    cert_lines = [line.strip()[:200] for line in text.splitlines() if re.search(r"\b(certified|certification|certificate)\b", line, re.I)][:5]
    extracted = {"skills": skills, "education": education_lines, "projects": projects, "certifications": cert_lines, "experience_excerpts": _experience_excerpts(text), "review_note": "Automated extraction may miss context. Experience excerpts are unverified source text; no experience level is inferred. Review every field before accepting."}
    draft_id = secrets.token_urlsafe(24)
    DRAFTS[draft_id] = (user_id, extracted, time.time() + 900, filename[:255])
    return {"draft_id": draft_id, "extracted": extracted}

def peek_draft(draft_id: str, user_id: int) -> tuple[dict, str]:
    draft = DRAFTS.get(draft_id)
    if not draft or draft[0] != user_id or draft[2] < time.time():
        if draft and draft[0] == user_id and draft[2] < time.time():
            DRAFTS.pop(draft_id, None)
        raise HTTPException(400, "This review draft expired. Upload the resume again.")
    return draft[1], draft[3]


def consume_draft(draft_id: str, user_id: int) -> tuple[dict, str]:
    extracted, filename = peek_draft(draft_id, user_id)
    DRAFTS.pop(draft_id, None)
    return extracted, filename
