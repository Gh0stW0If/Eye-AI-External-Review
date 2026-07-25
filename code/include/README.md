# Include Stage: PDF-to-Markdown, Dual-Model Judgement, and Debate

This module determines whether full-text articles have external validation evidence.

## Workflow

1. Convert PDF articles to Markdown and export original table/figure images.
2. Run GPT and Qwen separately through Step 1, Step 2, and Step 3. Each model produces one `external_validation` judgement.
3. Compare GPT and Qwen judgements.
4. If the judgements disagree, or if either judgement is unclear/empty/failed to parse, run one debate/adjudication round using both models' decisions and reasoning.
5. If GPT, Qwen, or the debate result is positive or unclear, route the article to manual review.

## Files

- `markdown_converter.py`: converts PDFs to Markdown and table/figure images using Docling.
- `pdf_to_markdown.py`: standalone PDF conversion CLI.
- `external_validation_screen.py`: single-model Step 1/2/3 judgement CLI for GPT and Qwen.
- `compare_results.py`: compares GPT/Qwen judgement CSVs and routes disagreement/manual-review cases.
- `debate_judgement.py`: debates only inconsistent or unclear cases and exports the final judgement plus manual-review list.
- `../../prompts/include/prompts.py`: Step 1, Step 2, and Step 3 prompts.
- `json_utils.py`: JSON parsing and CSV flattening helpers.
- `requirements.txt`: dependencies.

## Input Format

`external_validation_screen.py` supports:

1. A single PDF file.
2. A folder containing PDF files.
3. A CSV/Excel file containing PDF paths. Supported path columns: `PDF_Path`, `pdf_path`, `PDF`, `pdf`, `file_path`, `FilePath`.
4. An existing Markdown article root with `--input-type markdown`.

Markdown article folder format:

```text
mkd_root\paper_id\paper_id.md
mkd_root\paper_id\table_1.png
mkd_root\paper_id\table_images.json
```

## Convert PDFs To Markdown

```powershell
cd code\include
python pdf_to_markdown.py --input ".\examples\pdfs" --output-root ".\outputs\mkd"
```

OCR is disabled by default. Enable it with:

```powershell
python pdf_to_markdown.py --input ".\examples\pdfs" --output-root ".\outputs\mkd" --ocr
```

## GPT-5.4 Step 1/2/3 Judgement

PDF input is converted to Markdown first:

```powershell
python external_validation_screen.py --input ".\examples\pdfs" --provider openai --model gpt-5.4 --task-name cataract --mkd-root ".\outputs\mkd" --output-dir ".\outputs"
```

Existing Markdown input:

```powershell
python external_validation_screen.py --input ".\outputs\mkd" --input-type markdown --provider openai --model gpt-5.4 --task-name cataract --output-dir ".\outputs"
```

The script reads `OPENAI_API_KEY` from the environment or from a repository-root `.env` file. Use `public_information/.env.example` as the template. Output:

```text
outputs\cataract_openai_judgement.jsonl
outputs\cataract_openai_judgement.csv
```

## Qwen2.5-VL Step 1/2/3 Judgement

```powershell
python external_validation_screen.py --input ".\examples\pdfs" --provider qwen --model qwen2.5-vl --task-name cataract --mkd-root ".\outputs\mkd" --output-dir ".\outputs"
```

The script reads `QWEN_API_KEY` from the environment or from a repository-root `.env` file. Use `public_information/.env.example` as the template. Qwen Step 2 image input uses DashScope multimodal calls and temporary file upload.

Output:

```text
outputs\cataract_qwen_judgement.jsonl
outputs\cataract_qwen_judgement.csv
```

## Local Smoke Test

Validate PDF conversion, Markdown loading, image discovery, and output paths without API calls:

```powershell
python external_validation_screen.py --input ".\examples\one.pdf" --provider openai --model gpt-5.4 --task-name test_one --mkd-root ".\outputs\mkd" --limit 1 --dry-run
```

To skip Step 3 temporarily:

```powershell
python external_validation_screen.py --input ".\outputs\mkd" --input-type markdown --provider openai --task-name test_one --skip-judgement
```

## Compare GPT And Qwen Judgements

```powershell
python compare_results.py --left ".\outputs\cataract_openai_judgement.csv" --right ".\outputs\cataract_qwen_judgement.csv" --left-name GPT --right-name Qwen --output-dir ".\comparison_results"
```

Outputs:

- `*_comparison.csv`: all studies with side-by-side model decisions.
- `*_needs_debate.csv`: inconsistent or unclear studies.
- `*_manual_review.csv`: studies where either model is positive or unclear.

## Debate / Adjudication

By default, consistent `No/No` records are skipped:

```powershell
python debate_judgement.py --left ".\outputs\cataract_openai_judgement.jsonl" --right ".\outputs\cataract_qwen_judgement.jsonl" --left-name GPT --right-name Qwen --task-name cataract --provider openai --model gpt-5.4 --source-dir ".\outputs\mkd" --output-dir ".\debate_results"
```

Outputs:

```text
debate_results\cataract_debate_judgement.jsonl
debate_results\cataract_debate_judgement.csv
debate_results\cataract_manual_review_after_debate.csv
```

`cataract_manual_review_after_debate.csv` keeps records where GPT, Qwen, or debate is positive or unclear.

## Notes

- PDF conversion depends on `docling`.
- Qwen image input depends on `dashscope` and `requests`.
- Running this workflow calls model APIs and may incur cost.
- Consistent `external_validation=No` from GPT and Qwen does not enter debate or manual-review lists.

