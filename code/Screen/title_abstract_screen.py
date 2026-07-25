"""Run title/abstract four-step screening and export a structured CSV."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI



PROMPT_PLACEHOLDER_NOTE = (
    "PROMPT PLACEHOLDER: insert the approved title/abstract screening prompt "
    "from prompts/screen_prompts.xlsx before production use."
)


def build_step1_prompt(disease_key: str, disease_text: str | None = None) -> str:
    disease = disease_text or disease_key
    return f"{PROMPT_PLACEHOLDER_NOTE}\nStep 1 placeholder for disease scope and AI-method screening. Disease: {disease}."


STEP2_PROMPT = f"{PROMPT_PLACEHOLDER_NOTE}\nStep 2 placeholder for article-type and study-design exclusion."


def build_step3_prompt(disease_key: str) -> str:
    return f"{PROMPT_PLACEHOLDER_NOTE}\nStep 3 placeholder for task-type screening. Disease key: {disease_key}."


def get_step4_prompt(kind: str) -> str:
    return f"{PROMPT_PLACEHOLDER_NOTE}\nStep 4 placeholder for original image/video input screening. Mode: {kind}."
TITLE_COLUMNS = ("Title", "TITLE", "title")
ABSTRACT_COLUMNS = ("Abstract", "ABSTRACT", "abstract")
DECISION_COLUMNS = [
    "Response1", "Response1_decision", "Response1_confidence", "Response1_reason",
    "Response2", "Response2_decision", "Response2_confidence", "Response2_reason",
    "Response3", "Response3_decision", "Response3_confidence", "Response3_reason",
    "Disease_type", "Main_task",
    "Response4", "Response4_decision", "Response4_confidence", "Response4_reason",
]


class TaaScreeningClient:
    def __init__(self, api_key: str, model: str, sleep_seconds: float = 0.0) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.sleep_seconds = sleep_seconds

    def judge(self, title: str, abstract: str, prompt: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": f"Title: {title}\nAbstract: {abstract}\n\n{prompt}"}],
            temperature=0,
        )
        if self.sleep_seconds:
            time.sleep(self.sleep_seconds)
        text = response.choices[0].message.content or ""
        parsed = parse_json_response(text)
        parsed["_raw"] = json.dumps(
            {k: v for k, v in parsed.items() if k != "_raw"},
            ensure_ascii=False,
        )
        return parsed


def parse_json_response(text: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {
            "decision": "parse_error",
            "confidence": 0,
            "reason": f"No JSON object found in response: {text}",
        }
    raw = match.group(0)
    try:
        data = json.loads(raw)
    except Exception as exc:
        return {
            "decision": "parse_error",
            "confidence": 0,
            "reason": f"JSON parse error: {exc}; raw={raw}",
        }
    if not isinstance(data, dict):
        return {
            "decision": "parse_error",
            "confidence": 0,
            "reason": f"JSON response is not an object: {raw}",
        }
    return data


def is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def first_existing(columns: pd.Index, candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise ValueError(f"Missing required column. Tried: {', '.join(candidates)}")


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported input file type: {path.suffix}")


def collect_input_files(input_path: str | Path) -> list[Path]:
    path = Path(input_path)
    if path.is_file():
        return [path]
    files = sorted(
        p for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".xls"} and not p.name.startswith("~$")
    )
    return files


def ensure_output_columns(df: pd.DataFrame) -> None:
    for col in DECISION_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA


def write_result(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".xlsx":
        df.to_excel(output_path, index=False)
    else:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")


def default_output_path(input_file: Path, output_dir: Path | None, suffix: str) -> Path:
    parent = output_dir or input_file.parent
    stem = input_file.stem
    if suffix == "step3and4" and stem.endswith("step1and2"):
        stem = stem[: -len("step1and2")]
    return parent / f"{stem}{suffix}.csv"


def save_step_response(df: pd.DataFrame, index: int, step: int, data: dict[str, Any]) -> None:
    prefix = f"Response{step}"
    df.at[index, prefix] = data.get("_raw") or json.dumps(data, ensure_ascii=False)
    df.at[index, f"{prefix}_decision"] = data.get("decision", "")
    df.at[index, f"{prefix}_confidence"] = data.get("confidence", 0)
    df.at[index, f"{prefix}_reason"] = data.get("reason", "")
    if step == 3:
        df.at[index, "Disease_type"] = data.get("diseasetype", "")
        df.at[index, "Main_task"] = data.get("maintasks", "")


def run_four_steps(
    df: pd.DataFrame,
    client: TaaScreeningClient,
    disease: str,
    disease_text: str | None,
    step4_kind: str,
    resume: bool,
) -> pd.DataFrame:
    title_col = first_existing(df.columns, TITLE_COLUMNS)
    abstract_col = first_existing(df.columns, ABSTRACT_COLUMNS)
    ensure_output_columns(df)

    prompts = {
        1: build_step1_prompt(disease, disease_text),
        2: STEP2_PROMPT,
        3: build_step3_prompt(disease),
        4: get_step4_prompt(step4_kind),
    }

    for index, row in df.iterrows():
        title = "" if pd.isna(row[title_col]) else str(row[title_col])
        abstract = "" if pd.isna(row[abstract_col]) else str(row[abstract_col])
        if not title.strip() or not abstract.strip():
            continue

        print(f"Row {index + 1}: Step 1")
        if resume and pd.notna(row.get("Response1_decision")):
            step1 = {"decision": row.get("Response1_decision")}
        else:
            step1 = client.judge(title, abstract, prompts[1])
            save_step_response(df, index, 1, step1)
        if not is_true(step1.get("decision")):
            continue

        print(f"Row {index + 1}: Step 2")
        if resume and pd.notna(row.get("Response2_decision")):
            step2 = {"decision": row.get("Response2_decision")}
        else:
            step2 = client.judge(title, abstract, prompts[2])
            save_step_response(df, index, 2, step2)
        if not is_true(step2.get("decision")):
            continue

        print(f"Row {index + 1}: Step 3")
        if resume and pd.notna(row.get("Response3_decision")):
            step3 = {"decision": row.get("Response3_decision")}
        else:
            step3 = client.judge(title, abstract, prompts[3])
            save_step_response(df, index, 3, step3)
        if not is_true(step3.get("decision")):
            continue

        print(f"Row {index + 1}: Step 4")
        if resume and pd.notna(row.get("Response4_decision")):
            continue
        step4 = client.judge(title, abstract, prompts[4])
        save_step_response(df, index, 4, step4)

    return df


def process_file(args: argparse.Namespace, input_file: Path, api_key: str) -> Path:
    df = read_table(input_file)
    client = TaaScreeningClient(api_key=api_key, model=args.model, sleep_seconds=args.sleep)
    result = run_four_steps(
        df=df,
        client=client,
        disease=args.disease,
        disease_text=args.disease_text,
        step4_kind=args.step4_kind,
        resume=args.resume,
    )
    output_path = default_output_path(input_file, Path(args.output_dir) if args.output_dir else None, args.output_suffix)
    write_result(result, output_path)
    print(f"Saved: {output_path}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Title/abstract four-step screening")
    parser.add_argument("--input", required=True, help="CSV/Excel file or folder")
    parser.add_argument("--output-dir", default=None, help="Output folder. Defaults to input file folder")
    parser.add_argument("--output-suffix", default="step3and4", help="Suffix for output CSV filename")
    parser.add_argument("--disease", default="cataract", help="Disease key: cataract, amd, glaucoma, drdme, rop, ocularsurface, oculomics")
    parser.add_argument("--disease-text", default=None, help="Custom disease text for Step 1")
    parser.add_argument("--step4-kind", choices=["standard", "video", "anterior"], default="video")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep after each API call")
    parser.add_argument("--resume", action="store_true", help="Skip steps that already have decision columns")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    args = parse_args()
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing API key environment variable: {args.api_key_env}")
    files = collect_input_files(args.input)
    if not files:
        raise FileNotFoundError(f"No CSV/Excel files found at {args.input}")
    for input_file in files:
        process_file(args, input_file, api_key)


if __name__ == "__main__":
    main()








