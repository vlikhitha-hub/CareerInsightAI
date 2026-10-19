from __future__ import annotations
from collections import defaultdict
from math import isfinite
from statistics import fmean
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import EvaluationRun

METHODS = ("baseline", "ml", "ml_llm", "ml_rag_llm")
OPTIONAL_MEASURES = {
    "satisfaction": (1.0, 5.0, "satisfaction_mean_1_to_5", "satisfaction_sample_count"),
    "explanation_usefulness": (1.0, 5.0, "explanation_usefulness_mean_1_to_5", "explanation_usefulness_sample_count"),
    "response_time_ms": (0.0, 86_400_000.0, "response_time_ms_mean", "response_time_sample_count"),
}


def _validated_predictions(cases: list[dict], method: str) -> list[list[str]]:
    rows = []
    for case in cases:
        if not isinstance(case, dict):
            raise HTTPException(422, "Each evaluation case must be an object.")
        label = case.get("label")
        if not isinstance(label, str) or not label.strip() or len(label) > 160:
            raise HTTPException(422, "Every evaluation case needs a ground-truth career label of at most 160 characters.")
        predictions = case.get("predictions")
        row = predictions.get(method) if isinstance(predictions, dict) else None
        if not isinstance(row, list) or not row:
            raise HTTPException(422, f"Each case needs a ranked prediction list for {method}.")
        if any(not isinstance(candidate, str) or not candidate.strip() or len(candidate) > 160 for candidate in row):
            raise HTTPException(422, f"Predictions for {method} must be non-empty career labels of at most 160 characters.")
        rows.append([candidate.strip() for candidate in row])
    return rows


def _score(cases: list[dict], method: str) -> dict:
    truth = [case["label"].strip() for case in cases]
    top = _validated_predictions(cases, method)
    counts = defaultdict(lambda: [0, 0, 0])
    for actual, ranked in zip(truth, top):
        guess = ranked[0]
        if actual == guess:
            counts[actual][0] += 1
        else:
            counts[guess][1] += 1
            counts[actual][2] += 1
    precision = sum(v[0] / max(1, v[0] + v[1]) for v in counts.values()) / max(1, len(counts))
    recall = sum(v[0] / max(1, v[0] + v[2]) for v in counts.values()) / max(1, len(counts))
    per_class_f1 = [
        2 * (v[0] / max(1, v[0] + v[1])) * (v[0] / max(1, v[0] + v[2]))
        / max(1e-9, (v[0] / max(1, v[0] + v[1])) + (v[0] / max(1, v[0] + v[2])))
        for v in counts.values()
    ]
    f1 = sum(per_class_f1) / max(1, len(per_class_f1))
    top_k = sum(any(candidate == actual for candidate in ranked[:3]) for actual, ranked in zip(truth, top)) / len(cases)
    return {"precision_macro": round(precision, 4), "recall_macro": round(recall, 4), "f1_macro": round(f1, 4), "top_3_accuracy": round(top_k, 4)}


def _measured_metrics(cases: list[dict], method: str) -> dict:
    values = {key: [] for key in OPTIONAL_MEASURES}
    for case in cases:
        measurements = case.get("measurements", {})
        if measurements is None:
            measurements = {}
        if not isinstance(measurements, dict) or set(measurements) - set(METHODS):
            raise HTTPException(422, "Optional measurements must be grouped under baseline, ml, ml_llm or ml_rag_llm.")
        method_data = measurements.get(method, {})
        if method_data is None:
            method_data = {}
        if not isinstance(method_data, dict) or set(method_data) - set(OPTIONAL_MEASURES):
            raise HTTPException(422, f"Optional measurements for {method} contain an unsupported field.")
        for key, value in method_data.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
                raise HTTPException(422, f"The {key} measurement for {method} must be a finite number.")
            minimum, maximum, _, _ = OPTIONAL_MEASURES[key]
            if not minimum <= float(value) <= maximum:
                raise HTTPException(422, f"The {key} measurement for {method} must be between {minimum:g} and {maximum:g}.")
            values[key].append(float(value))
    result = {}
    for key, numbers in values.items():
        if numbers:
            _, _, mean_name, count_name = OPTIONAL_MEASURES[key]
            result[mean_name] = round(fmean(numbers), 4)
            result[count_name] = len(numbers)
    return result


def evaluate_and_store(db: Session, cases: list[dict], dataset_name: str) -> list[dict]:
    if not cases or len(cases) > 20000:
        raise HTTPException(422, "Provide between 1 and 20,000 labeled evaluation cases.")
    runs = []
    for method in METHODS:
        metrics = _score(cases, method)
        metrics.update(_measured_metrics(cases, method))
        row = EvaluationRun(name=f"{method} evaluation", method=method, dataset_name=dataset_name[:160], sample_count=len(cases), metrics=metrics)
        db.add(row)
        db.flush()
        runs.append(row)
    db.commit()
    return [{"id": row.id, "name": row.name, "method": row.method, "dataset_name": row.dataset_name, "sample_count": row.sample_count, "metrics": row.metrics, "created_at": row.created_at.isoformat()} for row in runs]


def list_runs(db: Session) -> list[dict]:
    rows = db.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc())).all()
    return [{"id": row.id, "name": row.name, "method": row.method, "dataset_name": row.dataset_name, "sample_count": row.sample_count, "metrics": row.metrics, "created_at": row.created_at.isoformat()} for row in rows]
