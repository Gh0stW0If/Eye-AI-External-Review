"""Convert PDFs to Markdown plus table/chart images using Docling.

Adapted from D:\work\AI-external\titleAndAbstractDecision\PDF2MKD.py.
Each PDF is converted into one article folder:

output_root/
  paper_stem/
    paper_stem.md
    table_1.png
    table_2.png
    table_images.json
    conversion_status.json
"""

from __future__ import annotations

import json
import traceback
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Iterable


def _convert_pdf_once(pdf_path: str | Path, output_dir: str | Path, images_scale: float, do_ocr: bool) -> dict:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pdf_file = Path(pdf_path)
    article_dir = Path(output_dir)
    article_dir.mkdir(parents=True, exist_ok=True)

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = do_ocr
    pipeline_options.do_table_structure = True
    pipeline_options.generate_table_images = True
    pipeline_options.images_scale = images_scale

    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)},
    )
    result = converter.convert(str(pdf_file))
    doc = result.document

    md_path = article_dir / f"{pdf_file.stem}.md"
    md_path.write_text(doc.export_to_markdown(), encoding="utf-8")

    image_names: list[str] = []
    for i, table in enumerate(doc.tables):
        if hasattr(table, "image") and table.image and table.image.pil_image:
            image_name = f"table_{i + 1}.png"
            table.image.pil_image.save(article_dir / image_name)
            image_names.append(image_name)

    (article_dir / "table_images.json").write_text(
        json.dumps(image_names, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    status = {
        "status": "ok",
        "pdf_path": str(pdf_file),
        "markdown": str(md_path),
        "image_count": len(image_names),
        "images": image_names,
    }
    (article_dir / "conversion_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return status


def _write_error_status(pdf_path: str | Path, output_dir: str | Path, exc: Exception) -> dict:
    error = {
        "status": "error",
        "pdf_path": str(pdf_path),
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }
    article_dir = Path(output_dir)
    article_dir.mkdir(parents=True, exist_ok=True)
    (article_dir / "conversion_status.json").write_text(
        json.dumps(error, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return error


def _conversion_worker(pdf_path: str, output_dir: str, queue: Queue, images_scale: float, do_ocr: bool) -> None:
    try:
        status = _convert_pdf_once(pdf_path, output_dir, images_scale, do_ocr)
        queue.put(("ok", status))
    except Exception as exc:
        error = _write_error_status(pdf_path, output_dir, exc)
        queue.put(("error", error))


def convert_pdf_safe(
    pdf_path: str | Path,
    output_dir: str | Path,
    timeout: int = 300,
    images_scale: float = 3.0,
    do_ocr: bool = False,
    overwrite: bool = False,
) -> tuple[str, dict]:
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    md_path = output_dir / f"{pdf_path.stem}.md"
    table_index = output_dir / "table_images.json"
    if not overwrite and md_path.exists() and table_index.exists():
        return "skip", {"status": "skip", "pdf_path": str(pdf_path), "markdown": str(md_path)}

    try:
        queue: Queue = Queue()
        process = Process(
            target=_conversion_worker,
            args=(str(pdf_path), str(output_dir), queue, images_scale, do_ocr),
        )
        process.start()
        try:
            status, payload = queue.get(timeout=timeout)
        except Exception:
            status = "error"
            payload = {
                "status": "error",
                "pdf_path": str(pdf_path),
                "error": f"Timeout after {timeout}s or process crashed",
            }
        finally:
            if process.is_alive():
                process.terminate()
                process.join()
        return status, payload
    except PermissionError:
        try:
            payload = _convert_pdf_once(pdf_path, output_dir, images_scale, do_ocr)
            payload["warning"] = "Subprocess timeout guard unavailable; converted in current process."
            return "ok", payload
        except Exception as exc:
            return "error", _write_error_status(pdf_path, output_dir, exc)


def collect_pdf_files(input_path: str | Path) -> list[Path]:
    path = Path(input_path)
    if path.is_file() and path.suffix.lower() == ".pdf":
        return [path]
    if path.is_dir():
        return sorted(path.glob("*.pdf"))
    raise ValueError(f"Expected a PDF file or PDF folder: {input_path}")


def convert_pdfs(
    pdf_files: Iterable[Path],
    output_root: str | Path,
    timeout: int = 300,
    images_scale: float = 3.0,
    do_ocr: bool = False,
    overwrite: bool = False,
) -> list[dict]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for pdf_file in pdf_files:
        article_dir = output_root / pdf_file.stem
        print(f"Converting PDF to Markdown: {pdf_file}")
        status, payload = convert_pdf_safe(
            pdf_file,
            article_dir,
            timeout=timeout,
            images_scale=images_scale,
            do_ocr=do_ocr,
            overwrite=overwrite,
        )
        payload["status"] = status
        results.append(payload)
        print(f"  {status}: {payload.get('error') or payload.get('markdown') or payload.get('image_count')}")
    (output_root / "conversion_manifest.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results
