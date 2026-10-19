from __future__ import annotations

def serialize_result(row: dict | None) -> dict | None:
    if row is None: return None
    return {key:value for key,value in row.items() if not key.startswith("_")}
