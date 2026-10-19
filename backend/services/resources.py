from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_RESOURCE_PATH = Path(__file__).resolve().parents[2] / "rag" / "learning_resources.json"


@lru_cache(maxsize=1)
def _resource_rows() -> tuple[dict[str, Any], ...]:
    try:
        payload = json.loads(_RESOURCE_PATH.read_text(encoding="utf-8"))
        rows = payload.get("resources", [])
        return tuple(
            row for row in rows
            if isinstance(row, dict)
            and isinstance(row.get("url"), str)
            and row["url"].startswith("https://")
            and isinstance(row.get("skills"), list)
        )
    except (OSError, json.JSONDecodeError, AttributeError):
        return ()


def _terms(value: str) -> set[str]:
    return {term.casefold() for term in re.findall(r"[a-z0-9+#.-]{2,}", value)}


def _public_resource(row: dict[str, Any]) -> dict[str, str]:
    return {key: str(row[key]) for key in ("id", "title", "provider", "url", "summary", "reviewed_on") if key in row}


def find_learning_resource(skill: str | None) -> dict[str, str] | None:
    if not skill:
        return None
    wanted = _terms(skill)
    for row in _resource_rows():
        aliases = {str(tag).casefold() for tag in row.get("skills", [])}
        if skill.casefold() in aliases or wanted & set().union(*(_terms(tag) for tag in aliases)):
            return _public_resource(row)
    return None


def resources_for_query(query: str, candidate_skills: list[str] | None = None, limit: int = 4) -> list[dict[str, str]]:
    rows = list(_resource_rows())
    query_terms = _terms(query)
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for index, row in enumerate(rows):
        tags = {str(tag).casefold() for tag in row.get("skills", [])}
        tag_terms = set().union(*(_terms(tag) for tag in tags)) if tags else set()
        overlap = len(query_terms & tag_terms)
        ranked.append((overlap, -index, row))
    matched = [row for score, _, row in sorted(ranked, reverse=True) if score > 0]
    selected = matched[:max(1, limit)]

    if len(selected) < limit:
        for skill in candidate_skills or []:
            resource = find_learning_resource(skill)
            if resource and all(item["id"] != resource["id"] for item in selected):
                original = next((row for row in rows if row.get("id") == resource["id"]), None)
                if original:
                    selected.append(original)
            if len(selected) >= limit:
                break
    return [_public_resource(row) for row in selected[:max(0, limit)]]
