from __future__ import annotations
import hashlib, os, secrets
from collections import deque
from datetime import datetime, timedelta
from math import ceil
from threading import Lock
from time import monotonic
from typing import Literal, cast
from fastapi import HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import User, UserSession, now_utc

_passwords = PasswordHash.recommended()
COOKIE_NAME = "career_session"
CSRF_NAME = "csrf_token"

def hash_password(password: str) -> str:
    return _passwords.hash(password)

def verify_password(password: str, encoded: str) -> bool:
    try: return _passwords.verify(password, encoded)
    except Exception: return False

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


_RATE_BUCKETS: dict[str, deque[float]] = {}
_RATE_LOCK = Lock()


def enforce_rate_limit(request: Request, action: str, subject: str, limit: int, window_seconds: int) -> None:
    """Apply an account/user-keyed sliding window without persisting identity values."""
    identity = (subject or (request.client.host if request.client else "unknown")).strip().casefold()
    bucket_key = hashlib.sha256(f"{action}:{identity}".encode("utf-8")).hexdigest()
    now = monotonic()
    cutoff = now - window_seconds
    with _RATE_LOCK:
        events = _RATE_BUCKETS.setdefault(bucket_key, deque())
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            retry_after = max(1, ceil(window_seconds - (now - events[0])))
            raise HTTPException(429, "Too many requests. Please wait before trying again.", headers={"Retry-After": str(retry_after)})
        events.append(now)
        if len(_RATE_BUCKETS) > 10000:
            for key, history in list(_RATE_BUCKETS.items()):
                while history and history[0] <= now - 3600:
                    history.popleft()
                if not history:
                    _RATE_BUCKETS.pop(key, None)

def cookie_settings() -> tuple[bool, Literal["lax", "strict", "none"]]:
    secure = os.getenv("COOKIE_SECURE", "true").strip().lower() in {"1", "true", "yes"}
    same_site = os.getenv("COOKIE_SAMESITE", "none" if secure else "lax").strip().lower()
    if same_site not in {"lax", "strict", "none"}: same_site = "none" if secure else "lax"
    return secure, cast(Literal["lax", "strict", "none"], same_site)

def issue_session(db: Session, response: Response, user: User, remember: bool = False) -> None:
    raw, csrf = secrets.token_urlsafe(36), secrets.token_urlsafe(30)
    max_age = 60 * 60 * 24 * 30 if remember else 60 * 60 * 12
    db.add(UserSession(user_id=user.id, token_hash=_digest(raw), csrf_hash=_digest(csrf), expires_at=now_utc() + timedelta(seconds=max_age)))
    db.commit()
    secure, same_site = cookie_settings()
    response.set_cookie(COOKIE_NAME, raw, httponly=True, secure=secure, samesite=same_site, max_age=max_age, path="/")
    response.set_cookie(CSRF_NAME, csrf, httponly=False, secure=secure, samesite=same_site, max_age=max_age, path="/")

def clear_session_cookies(response: Response) -> None:
    secure, same_site = cookie_settings()
    response.delete_cookie(COOKIE_NAME, path="/", secure=secure, httponly=True, samesite=same_site)
    response.delete_cookie(CSRF_NAME, path="/", secure=secure, httponly=False, samesite=same_site)

def issue_csrf_cookie(response: Response) -> str:
    token = secrets.token_urlsafe(30)
    secure, same_site = cookie_settings()
    response.set_cookie(CSRF_NAME, token, httponly=False, secure=secure, samesite=same_site, max_age=60*60*24*30, path="/")
    return token

def current_user(request: Request, db: Session) -> tuple[User, UserSession]:
    token = request.cookies.get(COOKIE_NAME)
    if not token: raise HTTPException(401, "Please sign in to continue.")
    session = db.scalar(select(UserSession).where(UserSession.token_hash == _digest(token), UserSession.revoked_at.is_(None)))
    if not session or session.expires_at < now_utc(): raise HTTPException(401, "Your session has expired. Please sign in again.")
    user = db.get(User, session.user_id)
    if not user or not user.is_active: raise HTTPException(401, "This account is not available.")
    return user, session

def require_csrf(request: Request, session: UserSession) -> None:
    cookie_token = request.cookies.get(CSRF_NAME, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not secrets.compare_digest(cookie_token, header_token) or not secrets.compare_digest(_digest(cookie_token), session.csrf_hash):
        raise HTTPException(403, "Security check failed. Refresh and try again.")
