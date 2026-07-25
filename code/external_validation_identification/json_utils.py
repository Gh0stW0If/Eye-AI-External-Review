"""JSON parsing and result-flattening helpers for external-validation-identification-stage screening."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_block(text: str) -> str | None:
    match = re.search(r"\{[\s\S]*\}", text or "")
    return match.group(0) if match else None


def parse_json_safely(text: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(text, dict):
        return text
    raw = text or ""
    candidates = [raw]
    block = extract_json_block(raw)
    if block and block != raw:
        candidates.append(block)
    for candidate in candidates:
        cleaned = candidate.strip().replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"parse_error": True, "raw_output": raw}


def to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def format_metrics(metrics: Any) -> str:
    if not isinstance(metrics, list):
        return "Not reported"
    parts: list[str] = []
    for metric in metrics:
        if not isinstance(metric, dict):
            parts.append(str(metric))
            continue
        name = metric.get("metric_name") or metric.get("metric") or "N/A"
        value = metric.get("value", "N/A")
        original = metric.get("original_text") or metric.get("text") or "N/A"
        location = metric.get("location", "N/A")
        parts.append(f"{name}: {value} ({original}, {location})")
    return " | ".join(parts) if parts else "Not reported"


def metric_value(metrics: Any, keywords: tuple[str, ...]) -> str:
    if not isinstance(metrics, list):
        return "Not reported"
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        name = str(metric.get("metric_name") or metric.get("metric") or "").upper()
        if any(keyword in name for keyword in keywords):
            return to_text(metric.get("value", "Not reported"))
    return "Not reported"


def flatten_initial_json(data: dict[str, Any], row_id: int | str = "") -> list[dict[str, Any]]:
    """Flatten first-pass Step1+Step2 output before final judgement."""
    step1 = data.get("step1", {}) if isinstance(data.get("step1"), dict) else {}
    step2 = data.get("step2", {}) if isinstance(data.get("step2"), dict) else {}
    base = {
        "id": row_id,
        "judgement_status": "not_run",
        "title": step1.get("title"),
        "authors": to_text(step1.get("authors")),
        "first_author_country": step1.get("first_author_country"),
        "last_corresponding_author_country": step1.get("last_corresponding_author_country"),
        "method": step1.get("method"),
        "task_objective": to_text(step1.get("task_objective")),
        "data_modality": to_text(step1.get("data_modality")),
        "diagnosed_diseases": to_text(step1.get("diagnosed_diseases")),
        "supervision_type": step1.get("supervision_type"),
        "validation_strategy": step1.get("validation_strategy"),
        "classification_type": step1.get("classification_type"),
        "external_validation": "Pending judgement",
        "RWS": "Pending judgement",
        "is_prospective": "Pending judgement",
        "RCT": "Pending judgement",
        "is_pilot": "Pending judgement",
        "extraction_notes": to_text(step1.get("extraction_notes")),
    }
    evidence = step2.get("datasets_evidence")
    if not isinstance(evidence, list) or not evidence:
        return [base]
    rows: list[dict[str, Any]] = []
    for dataset in evidence:
        if not isinstance(dataset, dict):
            continue
        row = dict(base)
        row["ds_name"] = dataset.get("dataset_name")
        row["ds_description"] = dataset.get("dataset_description")
        row["ds_type"] = dataset.get("dataset_type")
        row["ds_source"] = dataset.get("dataset_source")
        row["ds_country"] = dataset.get("dataset_country")
        row["ds_modality"] = dataset.get("dataset_modality")
        row["ds_real_world"] = dataset.get("is_real_world")
        row["ds_prospective"] = dataset.get("is_prospective")
        row["ds_RCT"] = dataset.get("is_RCT")
        row["ds_pop_country"] = dataset.get("population_country")
        row["sample_size_evidence"] = dataset.get("sample_size_evidence")
        row["all_metrics_details"] = format_metrics(dataset.get("metrics_list", []))
        row["location"] = dataset.get("location")
        rows.append(row)
    return rows or [base]


def flatten_final_json(data: dict[str, Any], row_id: int | str = "") -> list[dict[str, Any]]:
    notes = data.get("extraction_notes", {})
    notes_text = notes.get("reasoning", "") if isinstance(notes, dict) else to_text(notes)
    base = {
        "id": row_id,
        "judgement_status": "single_model_final",
        "title": data.get("title"),
        "authors": to_text(data.get("authors")),
        "first_author_country": data.get("first_author_country"),
        "last_corresponding_author_country": data.get("last_corresponding_author_country"),
        "method": data.get("method"),
        "task_objective": to_text(data.get("task_objective")),
        "data_modality": to_text(data.get("data_modality")),
        "diagnosed_diseases": to_text(data.get("diagnosed_diseases")),
        "supervision_type": data.get("supervision_type"),
        "validation_strategy": data.get("validation_strategy"),
        "classification_type": data.get("classification_type"),
        "external_validation": data.get("external_validation"),
        "RWS": data.get("is_rws_validation"),
        "is_prospective": data.get("is_prospective"),
        "RCT": data.get("is_rct"),
        "is_pilot": data.get("is_pilot"),
        "extraction_notes": notes_text,
    }
    datasets = data.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        return [base]

    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue
        row = dict(base)
        row["ds_name"] = dataset.get("name")
        row["ds_type"] = dataset.get("type")
        row["ds_source"] = dataset.get("source")
        row["ds_country"] = dataset.get("country")
        row["ds_prospective"] = dataset.get("prospective")
        row["ds_pop_country"] = dataset.get("population_country")
        row["ds_modality"] = dataset.get("modality")
        count = dataset.get("count", {}) if isinstance(dataset.get("count"), dict) else {}
        row["subjects"] = count.get("subjects", "Not reported")
        row["eyes"] = count.get("eyes", "Not reported")
        row["images"] = count.get("images", "Not reported")
        metrics = dataset.get("evaluation_metrics", [])
        row["all_metrics_details"] = format_metrics(metrics)
        row["AUC"] = metric_value(metrics, ("AUC", "AUROC", "AREA UNDER"))
        row["ACC"] = metric_value(metrics, ("ACC", "ACCURACY"))
        row["SEN"] = metric_value(metrics, ("SEN", "SENSITIVITY", "RECALL"))
        row["SPE"] = metric_value(metrics, ("SPE", "SPECIFICITY"))
        row["PPV"] = metric_value(metrics, ("PPV", "PRECISION"))
        row["F1"] = metric_value(metrics, ("F1",))
        row["KAPPA"] = metric_value(metrics, ("KAPPA",))
        rows.append(row)
    return rows or [base]

