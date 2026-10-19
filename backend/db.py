from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _load_local_environment() -> None:
    """Load simple KEY=value pairs for standalone development; platform env wins."""
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not key.isidentifier():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key, value)


_load_local_environment()


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip() or "sqlite:///./careerinsight.db"


def normalize_database_url(raw_url: str) -> tuple[str, dict]:
    """Convert driver-specific URL SSL JSON into PyMySQL's native SSL dictionary."""
    raw_url = raw_url.strip()
    if raw_url.startswith("mysql://"):
        raw_url = "mysql+pymysql://" + raw_url.removeprefix("mysql://")
    parsed = make_url(raw_url)
    query = dict(parsed.query)
    ssl_value = query.pop("ssl", None)
    ssl_args: dict = {}
    if ssl_value is not None:
        if isinstance(ssl_value, tuple):
            if len(ssl_value) != 1:
                raise ValueError("DATABASE_URL must not repeat the ssl query parameter.")
            ssl_value = ssl_value[0]
        value = str(ssl_value).strip()
        lowered = value.casefold()
        if lowered in {"1", "true", "yes", "on", "required"}:
            ssl_args = {"verify_mode": True}
        elif lowered in {"0", "false", "no", "off", "disabled"}:
            ssl_args = {"verify_mode": False}
        else:
            try:
                decoded = json.loads(value)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError("Unsupported DATABASE_URL ssl option; use a boolean or JSON SSL settings object.") from exc
            if not isinstance(decoded, dict):
                raise ValueError("DATABASE_URL ssl JSON option must be an object.")
            settings = dict(decoded)
            if "rejectUnauthorized" in settings:
                settings["verify_mode"] = bool(settings.pop("rejectUnauthorized"))
            allowed = {"ca", "capath", "cert", "key", "password", "check_hostname", "verify_mode", "cipher"}
            unexpected = set(settings) - allowed
            if unexpected:
                raise ValueError("Unsupported DATABASE_URL PyMySQL SSL setting.")
            ssl_args = settings or {"verify_mode": True}
    normalized = parsed.set(query=query).render_as_string(hide_password=False)
    return normalized, ({"ssl": ssl_args} if ssl_args else {})


def make_database_engine(raw_url: str | None = None, **overrides):
    normalized_url, ssl_connect_args = normalize_database_url(raw_url or _database_url())
    options = {"pool_pre_ping": True, "pool_recycle": 1800, **overrides}
    connect_args = dict(options.pop("connect_args", {}))
    if ssl_connect_args:
        connect_args.update(ssl_connect_args)
    if normalized_url.startswith("sqlite"):
        connect_args.setdefault("check_same_thread", False)
    if connect_args:
        options["connect_args"] = connect_args
    return create_engine(normalized_url, **options)


engine = make_database_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
