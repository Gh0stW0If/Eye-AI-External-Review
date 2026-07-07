"""Single-model full-text external-validation assessment.

Default workflow:
1. Convert PDFs to Markdown plus table/chart images with Docling.
2. Step 1 reads Markdown text only for basic study information.
3. Step 2 reads Markdown text plus extracted table/chart images for dataset and
   external-validation evidence.
4. Step 3 produces one model-level external-validation judgement.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import requests
import dashscope
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from json_utils import flatten_final_json, flatten_initial_json, parse_json_safely
from markdown_converter import convert_pdfs
from prompts import PROMPTS


PDF_COLUMNS = ("PDF_Path", "pdf_path", "PDF", "pdf", "file_path", "FilePath")

def get_qwen_upload_policy(api_key: str, model_name: str) -> dict[str, Any]:
    response = requests.get(
        "https://dashscope.aliyuncs.com/api/v1/uploads",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        params={"action": "getPolicy", "model": model_name},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["data"]


def upload_qwen_file_and_get_url(api_key: str, model_name: str, file_path: Path) -> str:
    policy = get_qwen_upload_policy(api_key, model_name)
    file_name = file_path.name
    key = f"{policy['upload_dir']}/{file_name}"
    with file_path.open("rb") as f:
        files = {
            "OSSAccessKeyId": (None, policy["oss_access_key_id"]),
            "Signature": (None, policy["signature"]),
            "policy": (None, policy["policy"]),
            "x-oss-object-acl": (None, policy["x_oss_object_acl"]),
            "x-oss-forbid-overwrite": (None, policy["x_oss_forbid_overwrite"]),
            "key": (None, key),
            "success_action_status": (None, "200"),
            "file": (file_name, f),
        }
        response = requests.post(policy["upload_host"], files=files, timeout=120)
    response.raise_for_status()
    return f"oss://{key}"

class ExternalValidationRunner:
    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        output_dir: Path,
        base_url: str | None = None,
        sleep_seconds: float = 0.0,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        self.model = model
        self.output_dir = output_dir
        self.sleep_seconds = sleep_seconds
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def assess_article_dir(self, article_dir: Path, paper_id: str | int = "", run_judgement: bool = True) -> dict[str, Any]:
        md_path, image_paths = load_markdown_article(article_dir)
        print(f"Assessing Markdown article: {article_dir}")
        md_content = md_path.read_text(encoding="utf-8", errors="ignore")

        step1 = self._markdown_prompt(PROMPTS["step1"], md_content, [])
        step2 = self._markdown_prompt(PROMPTS["step2"], md_content, image_paths)

        step1_json = parse_json_safely(step1)
        step2_json = parse_json_safely(step2)
        initial_json = {"step1": step1_json, "step2": step2_json}
        result = {
            "paper_id": paper_id or article_dir.name,
            "article_dir": str(article_dir),
            "markdown_path": str(md_path),
            "image_paths": [str(p) for p in image_paths],
            "step1_raw": step1,
            "step2_raw": step2,
            "initial_json": initial_json,
            "judgement_run": run_judgement,
        }
        if run_judgement:
            step3_input = f"""
Please generate the final JSON based on the following extracted information.

--- Step 1: Basic Information ---
{step1}

--- Step 2: Dataset Evidence ---
{step2}

--- Original Markdown Text Context ---
{md_content}
"""
            step3 = self._text_prompt(PROMPTS["step3"], step3_input)
            result["step3_raw"] = step3
            result["final_json"] = parse_json_safely(step3)
        return result

    def _markdown_prompt(self, prompt: str, md_content: str, image_paths: list[Path]) -> str:
        if self.provider == "openai":
            content: list[dict[str, Any]] = [
                {"type": "input_text", "text": f"Article Markdown Text:\n{md_content}"}
            ]
            for image_path in image_paths:
                uploaded = self._upload_openai_file(image_path)
                content.append({"type": "input_text", "text": f"Extracted original table/chart image: {image_path.name}"})
                content.append({"type": "input_image", "file_id": uploaded.id})
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content},
                ],
                temperature=0,
            )
            if self.sleep_seconds:
                time.sleep(self.sleep_seconds)
            return response.output_text

        if image_paths:
            content_list: list[dict[str, Any]] = [
                {"text": prompt},
                {"text": f"Article Markdown Text:\n{md_content}"},
            ]
            for image_path in image_paths:
                image_url = upload_qwen_file_and_get_url(self.api_key, self.model, image_path)
                content_list.append({"text": f"Extracted original table/chart image: {image_path.name}"})
                content_list.append({"image": image_url})
            response = dashscope.MultiModalConversation.call(
                api_key=self.api_key,
                model=self.model,
                messages=[{"role": "user", "content": content_list}],
                response_format={"type": "json_object"},
            )
            if self.sleep_seconds:
                time.sleep(self.sleep_seconds)
            return response.output.choices[0].message.content[0]["text"]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Article Markdown Text:\n{md_content}"},
            ],
            temperature=0,
        )
        if self.sleep_seconds:
            time.sleep(self.sleep_seconds)
        return response.choices[0].message.content or ""
    def _text_prompt(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "openai":
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            return response.output_text
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""

    def _upload_openai_file(self, path: Path) -> Any:
        with path.open("rb") as f:
            return self.client.files.create(file=f, purpose="user_data")


def first_existing(columns: pd.Index, candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise ValueError(f"Missing PDF path column. Tried: {', '.join(candidates)}")


def collect_pdf_records(input_path: Path) -> list[tuple[str, Path]]:
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [(input_path.stem, input_path)]
    if input_path.is_dir():
        return [(p.stem, p) for p in sorted(input_path.glob("*.pdf"))]
    df = pd.read_csv(input_path) if input_path.suffix.lower() == ".csv" else pd.read_excel(input_path)
    pdf_col = first_existing(df.columns, PDF_COLUMNS)
    records: list[tuple[str, Path]] = []
    for idx, row in df.iterrows():
        raw_path = row.get(pdf_col)
        if pd.isna(raw_path) or not str(raw_path).strip() or str(raw_path).strip() == "无下载链接":
            continue
        paper_id = row.get("id", row.get("ID", row.get("PMID", idx + 1)))
        records.append((str(paper_id), Path(str(raw_path))))
    return records


def collect_markdown_records(markdown_root: Path) -> list[tuple[str, Path]]:
    if markdown_root.is_file() and markdown_root.suffix.lower() == ".md":
        return [(markdown_root.stem, markdown_root.parent)]
    article_dirs = []
    if any(markdown_root.glob("*.md")):
        article_dirs.append((markdown_root.name, markdown_root))
    for child in sorted(markdown_root.iterdir() if markdown_root.exists() else []):
        if child.is_dir() and any(child.glob("*.md")):
            article_dirs.append((child.name, child))
    return article_dirs


def load_markdown_article(article_dir: Path) -> tuple[Path, list[Path]]:
    md_files = sorted(article_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No .md file found in {article_dir}")
    md_path = md_files[0]
    image_paths: list[Path] = []
    table_index = article_dir / "table_images.json"
    if table_index.exists():
        try:
            image_names = json.loads(table_index.read_text(encoding="utf-8"))
            image_paths = [article_dir / name for name in image_names if (article_dir / name).exists()]
        except Exception:
            image_paths = []
    if not image_paths:
        image_paths = sorted([*article_dir.glob("*.png"), *article_dir.glob("*.jpg"), *article_dir.glob("*.jpeg")])
    return md_path, image_paths


def prepare_markdown_records(args: argparse.Namespace) -> list[tuple[str, Path]]:
    input_path = Path(args.input)
    if args.input_type == "markdown":
        return collect_markdown_records(input_path)

    pdf_records = collect_pdf_records(input_path)
    if args.limit is not None:
        pdf_records = pdf_records[: args.limit]
    mkd_root = Path(args.mkd_root) if args.mkd_root else Path(args.output_dir) / "mkd"
    convert_pdfs(
        [pdf for _, pdf in pdf_records],
        mkd_root,
        timeout=args.convert_timeout,
        images_scale=args.images_scale,
        do_ocr=args.ocr,
        overwrite=args.overwrite_mkd,
    )
    return [(paper_id, mkd_root / pdf.stem) for paper_id, pdf in pdf_records]


def save_outputs(results: list[dict[str, Any]], output_dir: Path, task_name: str, provider: str, run_judgement: bool = True) -> tuple[Path, Path]:
    stage = "judgement" if run_judgement else "firstpass"
    jsonl_path = output_dir / f"{task_name}_{provider}_{stage}.jsonl"
    csv_path = output_dir / f"{task_name}_{provider}_{stage}.csv"
    rows: list[dict[str, Any]] = []
    with jsonl_path.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            if result.get("judgement_run") and result.get("final_json"):
                flat_rows = flatten_final_json(result.get("final_json", {}), result.get("paper_id", ""))
            else:
                flat_rows = flatten_initial_json(result.get("initial_json", {}), result.get("paper_id", ""))
            for row in flat_rows:
                row["article_dir"] = result.get("article_dir", "")
                row["markdown_path"] = result.get("markdown_path", "")
                rows.append(row)
    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
    return jsonl_path, csv_path


def default_model(provider: str) -> str:
    if provider == "openai":
        return "gpt-5.4"
    return "qwen2.5-vl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single-model external-validation judgement from Markdown+images")
    parser.add_argument("--input", required=True, help="PDF file/folder, CSV/Excel with PDF_Path, or Markdown article/root")
    parser.add_argument("--input-type", choices=["pdf", "markdown"], default="pdf")
    parser.add_argument("--mkd-root", default=None, help="Markdown output root for PDF conversion")
    parser.add_argument("--output-dir", default="outputs", help="Output folder")
    parser.add_argument("--task-name", default="include", help="Output filename prefix")
    parser.add_argument("--provider", choices=["openai", "qwen"], default="openai")
    parser.add_argument("--model", default=None, help="Model name; defaults to gpt-5.4 or qwen2.5-vl")
    parser.add_argument("--api-key-env", default=None, help="API key environment variable")
    parser.add_argument("--base-url", default=None, help="Optional OpenAI-compatible base URL, e.g. DashScope")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for testing")
    parser.add_argument("--skip-judgement", action="store_true", help="Only run Step 1 and Step 2; default runs Step 3 judgement")
    parser.add_argument("--run-judgement", action="store_true", help="Deprecated; Step 3 judgement now runs by default")
    parser.add_argument("--dry-run", action="store_true", help="Validate conversion and Markdown/image loading without API calls")
    parser.add_argument("--convert-timeout", type=int, default=300)
    parser.add_argument("--images-scale", type=float, default=3.0)
    parser.add_argument("--ocr", action="store_true", help="Enable Docling OCR during PDF conversion")
    parser.add_argument("--overwrite-mkd", action="store_true", help="Overwrite existing Markdown conversion")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    provider = args.provider
    model = args.model or default_model(provider)
    base_url = args.base_url
    if provider == "qwen" and not base_url:
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    records = prepare_markdown_records(args)
    if args.input_type == "markdown" and args.limit is not None:
        records = records[: args.limit]
    if not records:
        raise FileNotFoundError(f"No processable articles found from input: {args.input}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        results = []
        for paper_id, article_dir in records:
            md_path, image_paths = load_markdown_article(article_dir)
            md_content = md_path.read_text(encoding="utf-8", errors="ignore")
            results.append({
                "paper_id": paper_id,
                "article_dir": str(article_dir),
                "markdown_path": str(md_path),
                "image_paths": [str(p) for p in image_paths],
                "markdown_chars": len(md_content),
                "image_count": len(image_paths),
                "dry_run": True,
                "judgement_run": False,
                "initial_json": {"step1": {}, "step2": {}},
            })
        jsonl_path, csv_path = save_outputs(results, output_dir, args.task_name, provider, False)
        print("Dry run only; no API calls were made.")
        print(f"Saved JSONL: {jsonl_path}")
        print(f"Saved CSV: {csv_path}")
        return

    api_key_env = args.api_key_env or ("OPENAI_API_KEY" if provider == "openai" else "QWEN_API_KEY")
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing API key environment variable: {api_key_env}")

    runner = ExternalValidationRunner(
        provider=provider,
        api_key=api_key,
        model=model,
        output_dir=output_dir,
        base_url=base_url,
        sleep_seconds=args.sleep,
    )
    results = []
    for paper_id, article_dir in records:
        try:
            results.append(runner.assess_article_dir(article_dir, paper_id=paper_id, run_judgement=not args.skip_judgement))
        except Exception as exc:
            results.append({
                "paper_id": paper_id,
                "article_dir": str(article_dir),
                "error": str(exc),
                "initial_json": {"step1": {}, "step2": {"parse_error": True, "raw_output": str(exc)}},
            })
    jsonl_path, csv_path = save_outputs(results, output_dir, args.task_name, provider, not args.skip_judgement)
    print(f"Saved JSONL: {jsonl_path}")
    print(f"Saved CSV: {csv_path}")


if __name__ == "__main__":
    main()











