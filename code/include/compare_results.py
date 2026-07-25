"""Compare GPT/Qwen external-validation judgements and route debate/manual review."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


DECISION_COLUMNS = ["external_validation"]
KEY_CANDIDATES = ["id", "title", "pdf_path", "markdown_path"]
UNCLEAR_VALUES = {
    "",
    "unclear",
    "uncertain",
    "unknown",
    "not reported",
    "pending judgement",
    "pending",
    "na",
    "n/a",
    "parse_error",
    "error",
}


def normalize(value: object) -> str:
    if pd.isna(value):
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


def is_manual_trigger(value: str) -> bool:
    return value in {"yes", "unclear"} or value not in {"yes", "no"}


def choose_key(left: pd.DataFrame, right: pd.DataFrame, preferred: str | None) -> str:
    if preferred:
        if preferred not in left.columns or preferred not in right.columns:
            raise ValueError(f"Preferred key column not present in both files: {preferred}")
        return preferred
    for key in KEY_CANDIDATES:
        if key in left.columns and key in right.columns:
            return key
    raise ValueError(f"No shared key column found. Tried: {', '.join(KEY_CANDIDATES)}")


def first_nonempty(values: list[Any]) -> Any:
    for value in values:
        if pd.notna(value) and str(value).strip():
            return value
    return ""


def paper_level(df: pd.DataFrame, key: str) -> pd.DataFrame:
    rows = []
    for key_value, group in df.groupby(key, dropna=False):
        row = {key: key_value}
        for col in ["title", "markdown_path", "article_dir", "extraction_notes"]:
            if col in group.columns:
                row[col] = first_nonempty(group[col].tolist())
        if "external_validation" in group.columns:
            decisions = [normalize(v) for v in group["external_validation"].tolist()]
            row["external_validation"] = next((v for v in decisions if v == "yes"), next((v for v in decisions if v == "unclear"), next((v for v in decisions if v), "unclear")))
        else:
            row["external_validation"] = "unclear"
        rows.append(row)
    return pd.DataFrame(rows)


def compare(left_path: Path, right_path: Path, output_dir: Path, left_name: str, right_name: str, key: str | None) -> tuple[Path, Path, Path]:
    left_raw = pd.read_csv(left_path)
    right_raw = pd.read_csv(right_path)
    key_col = choose_key(left_raw, right_raw, key)
    left = paper_level(left_raw, key_col)
    right = paper_level(right_raw, key_col)
    merged = left.merge(right, on=key_col, how="outer", suffixes=(f"_{left_name}", f"_{right_name}"))

    left_col = f"external_validation_{left_name}"
    right_col = f"external_validation_{right_name}"
    merged[f"{left_name}_decision"] = merged[left_col].map(normalize) if left_col in merged.columns else "unclear"
    merged[f"{right_name}_decision"] = merged[right_col].map(normalize) if right_col in merged.columns else "unclear"
    merged["decision_consistent"] = merged[f"{left_name}_decision"] == merged[f"{right_name}_decision"]
    merged["has_unclear"] = (merged[f"{left_name}_decision"] == "unclear") | (merged[f"{right_name}_decision"] == "unclear")
    merged["needs_debate"] = (~merged["decision_consistent"]) | merged["has_unclear"]
    merged["manual_review_required"] = merged[f"{left_name}_decision"].map(is_manual_trigger) | merged[f"{right_name}_decision"].map(is_manual_trigger)

    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = output_dir / f"{left_path.stem}_vs_{right_path.stem}_comparison.csv"
    debate_path = output_dir / f"{left_path.stem}_vs_{right_path.stem}_needs_debate.csv"
    manual_path = output_dir / f"{left_path.stem}_vs_{right_path.stem}_manual_review.csv"
    merged.to_csv(comparison_path, index=False, encoding="utf-8-sig")
    merged[merged["needs_debate"]].to_csv(debate_path, index=False, encoding="utf-8-sig")
    merged[merged["manual_review_required"]].to_csv(manual_path, index=False, encoding="utf-8-sig")
    return comparison_path, debate_path, manual_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare GPT/Qwen include-stage judgement CSV outputs")
    parser.add_argument("--left", required=True, help="First model judgement CSV, e.g. GPT")
    parser.add_argument("--right", required=True, help="Second model judgement CSV, e.g. Qwen")
    parser.add_argument("--left-name", default="GPT")
    parser.add_argument("--right-name", default="Qwen")
    parser.add_argument("--key", default=None, help="Optional merge key column")
    parser.add_argument("--output-dir", default="comparison_results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison_path, debate_path, manual_path = compare(
        Path(args.left),
        Path(args.right),
        Path(args.output_dir),
        args.left_name,
        args.right_name,
        args.key,
    )
    print(f"Saved comparison: {comparison_path}")
    print(f"Saved needs-debate list: {debate_path}")
    print(f"Saved manual-review list: {manual_path}")


if __name__ == "__main__":
    main()
