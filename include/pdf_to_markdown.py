"""CLI wrapper for PDF -> Markdown/table-image conversion."""

from __future__ import annotations

import argparse
from pathlib import Path

from markdown_converter import collect_pdf_files, convert_pdfs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PDFs to Markdown plus table/chart images")
    parser.add_argument("--input", required=True, help="PDF file or folder containing PDFs")
    parser.add_argument("--output-root", required=True, help="Output Markdown root")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--images-scale", type=float, default=3.0)
    parser.add_argument("--ocr", action="store_true", help="Enable Docling OCR")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdfs = collect_pdf_files(Path(args.input))
    convert_pdfs(
        pdfs,
        args.output_root,
        timeout=args.timeout,
        images_scale=args.images_scale,
        do_ocr=args.ocr,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
