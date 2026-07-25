"""Debate/adjudication stage for external-validation assessment.

Run after GPT and Qwen have each completed Step 1, Step 2, and Step 3. By
default this script only debates papers where the two model-level judgements are
inconsistent or at least one judgement is unclear.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from json_utils import flatten_final_json, parse_json_safely


DEBATE_PROMPT = """Role: You are a senior medical AI evidence adjudicator.
Your task is to produce the final high-confidence external-validation judgement
by reconciling two AI-generated extraction results using the source text as the
highest-priority authority when source text is available.

Inputs:
- source_text: full text or key sections from the article. This is the highest-priority evidence.
- result_A: Step 1, Step 2, and Step 3 extraction/judgement from model A.
- result_B: Step 1, Step 2, and Step 3 extraction/judgement from model B.

Adjudication rules:
1) Source truth has highest priority. If result_A and result_B conflict, use source_text to decide. If source_text is unavailable or does not resolve the conflict, set external_validation="Unclear" and explain.
2) Use evidence-first judgement. Do not infer external validation from vague wording.
3) External validation is Yes only when an independent test/validation dataset is clearly separate from model development data and has explicitly reported performance metrics.
4) Random split, cross-validation folds, same-institution repartitioning, or temporal split alone are not external validation unless explicitly described as an independent external cohort.
5) Retain the most granular dataset-level evidence from both results when source text supports it.
6) Standardize metric names to uppercase and convert percentages to decimals between 0 and 1 when possible.
7) If external_validation is Yes, name at least one external validation dataset in extraction_notes.reasoning.
8) If the evidence remains ambiguous, use external_validation="Unclear" rather than forcing Yes or No.

Return ONLY valid JSON using this schema:
{
  "title": "",
  "authors": [],
  "first_author_country": "",
  "last_corresponding_author_country": "",
  "method": "",
  "task_objective": [],
  "data_modality": [],
  "diagnosed_diseases": [],
  "supervision_type": "",
  "validation_strategy": "",
  "classification_type": "",
  "external_validation": "Yes/No/Unclear",
  "extraction_notes": {
    "reasoning": "",
    "conflict_flag": false
  },
  "datasets": [
    {
      "type": "development/internal validation/external validation/unclear",
      "name": "",
      "modality": "",
      "source": "",
      "country": "",
      "prospective": "Yes/No/NA",
      "population_country": "",
      "count": {
        "subjects": "Not reported",
        "eyes": "Not reported",
        "images": "Not reported"
      },
      "evaluation_metrics": [
        {
          "metric_name": "",
          "value": "",
          "original_text": "",
          "location": ""
        }
      ],
      "conflict_flag": false
    }
  ],
  "conflict_report": [
    {"field": "", "reasoning": ""}
  ]
}
"""

UNCLEAR_VALUES = {"", "unclear", "uncertain", "unknown", "not reported", "pending judgement", "pending", "na", "n/a", "parse_error", "error"}


def normalize_decision(value: Any) -> str:
    if value is None:
        return "unclear"
    text = str(value).strip().lower()
    mapping = {
        "yes": "yes",
        "y": "yes",
        "true": "yes",
        "1": "yes",
        "external validation": "yes",
        "no": "no",
        "n": "no",
        "false": "no",
        "0": "no",
        "no external validation": "no",
    }
    if text in mapping:
        return mapping[text]
    if text in UNCLEAR_VALUES or "unclear" in text or "uncertain" in text:
        return "unclear"
    return text


def manual_review_required(*decisions: str) -> bool:
    return any(decision in {"yes", "unclear"} or decision not in {"yes", "no"} for decision in decisions)


def decision_from_record(record: dict[str, Any]) -> str:
    final_json = record.get("final_json") if isinstance(record, dict) else None
    if isinstance(final_json, dict):
        if final_json.get("parse_error"):
            return "unclear"
        return normalize_decision(final_json.get("external_validation"))
    return "unclear"


def needs_debate(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_decision = decision_from_record(left)
    right_decision = decision_from_record(right)
    return left_decision != right_decision or left_decision == "unclear" or right_decision == "unclear"


def load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            key = str(obj.get("paper_id") or obj.get("pdf_path") or len(records) + 1)
            records[key] = obj
    return records


def model_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "step1_step2": record.get("initial_json"),
        "step3_final_judgement": record.get("final_json"),
        "step1_raw": record.get("step1_raw"),
        "step2_raw": record.get("step2_raw"),
        "step3_raw": record.get("step3_raw"),
        "error": record.get("error"),
    }


def find_source_text(source_dir: Path | None, paper_id: str, left: dict[str, Any], right: dict[str, Any]) -> str:
    for rec in (left, right):
        markdown_path = rec.get("markdown_path")
        if markdown_path and Path(str(markdown_path)).exists():
            return Path(str(markdown_path)).read_text(encoding="utf-8", errors="ignore")
    if not source_dir:
        return ""
    candidates = [paper_id]
    for rec in (left, right):
        for field in ("pdf_path", "markdown_path", "article_dir"):
            value = rec.get(field)
            if value:
                candidates.append(Path(str(value)).stem)
    seen = {c for c in candidates if c}
    for stem in seen:
        for path in source_dir.rglob("*.md"):
            if path.stem == stem or stem in path.stem or path.stem in stem:
                return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def call_model(client: OpenAI, provider: str, model: str, prompt: str, payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    if provider == "openai":
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
        return response.output_text
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def run_debate(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    provider = args.provider
    api_key_env = args.api_key_env or ("OPENAI_API_KEY" if provider == "openai" else "QWEN_API_KEY")
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing API key environment variable: {api_key_env}")
    base_url = args.base_url
    if provider == "qwen" and not base_url:
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    left_records = load_jsonl(Path(args.left))
    right_records = load_jsonl(Path(args.right))
    all_keys = sorted(set(left_records) | set(right_records))
    source_dir = Path(args.source_dir) if args.source_dir else None
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / f"{args.task_name}_debate_judgement.jsonl"
    csv_path = output_dir / f"{args.task_name}_debate_judgement.csv"
    manual_path = output_dir / f"{args.task_name}_manual_review_after_debate.csv"
    rows: list[dict[str, Any]] = []
    manual_rows: list[dict[str, Any]] = []

    with jsonl_path.open("w", encoding="utf-8") as f:
        for key in all_keys:
            left = left_records.get(key, {})
            right = right_records.get(key, {})
            left_decision = decision_from_record(left)
            right_decision = decision_from_record(right)
            route_to_debate = args.include_consistent or needs_debate(left, right)
            if not route_to_debate:
                continue
            source_text = find_source_text(source_dir, key, left, right)
            payload = {
                "paper_id": key,
                "source_text": source_text,
                "result_A_name": args.left_name,
                "result_A_decision": left_decision,
                "result_A": model_payload(left),
                "result_B_name": args.right_name,
                "result_B_decision": right_decision,
                "result_B": model_payload(right),
            }
            try:
                raw = call_model(client, provider, args.model, DEBATE_PROMPT, payload)
                final_json = parse_json_safely(raw)
                debate_decision = normalize_decision(final_json.get("external_validation") if isinstance(final_json, dict) else None)
                record = {
                    "paper_id": key,
                    "left_name": args.left_name,
                    "right_name": args.right_name,
                    "left_decision": left_decision,
                    "right_decision": right_decision,
                    "debate_decision": debate_decision,
                    "needs_debate": True,
                    "manual_review_required": manual_review_required(left_decision, right_decision, debate_decision),
                    "source_text_used": bool(source_text),
                    "debate_raw": raw,
                    "final_json": final_json,
                }
            except Exception as exc:
                record = {
                    "paper_id": key,
                    "left_name": args.left_name,
                    "right_name": args.right_name,
                    "left_decision": left_decision,
                    "right_decision": right_decision,
                    "debate_decision": "unclear",
                    "needs_debate": True,
                    "manual_review_required": True,
                    "source_text_used": bool(source_text),
                    "error": str(exc),
                    "final_json": {"parse_error": True, "raw_output": str(exc)},
                }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            flat_rows = flatten_final_json(record.get("final_json", {}), key)
            for row in flat_rows:
                row["judgement_status"] = "debate_final"
                row[f"{args.left_name}_decision"] = left_decision
                row[f"{args.right_name}_decision"] = right_decision
                row["debate_decision"] = record["debate_decision"]
                row["needs_debate"] = True
                row["manual_review_required"] = record["manual_review_required"]
                rows.append(row)
                if record["manual_review_required"]:
                    manual_rows.append(row)

    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(manual_rows).to_csv(manual_path, index=False, encoding="utf-8-sig")
    return jsonl_path, csv_path, manual_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debate/adjudicate inconsistent or unclear include-stage judgements")
    parser.add_argument("--left", required=True, help="First judgement JSONL output")
    parser.add_argument("--right", required=True, help="Second judgement JSONL output")
    parser.add_argument("--left-name", default="GPT")
    parser.add_argument("--right-name", default="Qwen")
    parser.add_argument("--source-dir", default=None, help="Optional Markdown root used as source-text anchor")
    parser.add_argument("--output-dir", default="debate_results")
    parser.add_argument("--task-name", default="include")
    parser.add_argument("--provider", choices=["openai", "qwen"], default="openai")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--include-consistent", action="store_true", help="Debate all records, including consistent Yes/No records")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    jsonl_path, csv_path, manual_path = run_debate(parse_args())
    print(f"Saved debate JSONL: {jsonl_path}")
    print(f"Saved debate CSV: {csv_path}")
    print(f"Saved manual-review CSV: {manual_path}")


if __name__ == "__main__":
    main()


