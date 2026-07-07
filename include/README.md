# Include Stage: PDF 转 Markdown、双模型外部验证判断与 Debate

本目录用于对标题摘要筛选后纳入的全文 PDF 判断是否具有外部验证。代码整理自：

- `D:\work\AI-external\titleAndAbstractDecision\PDF2MKD.py`
- `D:\work\AI-external\titleAndAbstractDecision`
- `G:\allMKD`
- `G:\ai-external\Manuscript_May_12_v16.docx`

## 当前正式流程

1. PDF 文章先转为 Markdown，并导出原始表格/图表图片。
2. GPT 和 Qwen 分别完成 Step 1、Step 2、Step 3，并各自给出一次 `external_validation` 判断。
3. 比较 GPT 和 Qwen 的判断是否一致。
4. 如果判断不一致，或任一模型为 unclear/解析失败/空值，则结合双方判断和 reason 进行一轮 debate/adjudication。
5. 最后，如果 GPT、Qwen 或 debate 中至少一个判断为有外部验证或不确定，则进入人工判断。

## 文件说明

- `markdown_converter.py`：用 Docling 将 PDF 转 Markdown，并导出表格/图表图片。
- `pdf_to_markdown.py`：独立 PDF 转换入口。
- `external_validation_screen.py`：单模型 Step 1/2/3 判断入口，支持 GPT 和 Qwen。
- `compare_results.py`：比较 GPT/Qwen judgement CSV，输出一致性、是否需要 debate、是否需要人工判断。
- `debate_judgement.py`：只对不一致或 unclear 的记录进行 debate，输出 debate judgement 和 debate 后人工判断清单。
- `prompts.py`：Step 1、Step 2、Step 3 提示词。
- `json_utils.py`：JSON 解析和 CSV 扁平化。
- `requirements.txt`：依赖列表。

## 输入格式

`external_validation_screen.py` 支持：

1. 单个 PDF 文件。
2. 包含多个 PDF 的文件夹。
3. CSV/Excel 文件，需包含 PDF 路径列。支持列名：`PDF_Path`、`pdf_path`、`PDF`、`pdf`、`file_path`、`FilePath`。
4. 已转换好的 Markdown article root，使用 `--input-type markdown`。

Markdown article folder 格式：

```text
mkd_root\paper_id\paper_id.md
mkd_root\paper_id\table_1.png
mkd_root\paper_id\table_images.json
```

## 单独执行 PDF 转 Markdown

```powershell
cd G:\ai-external\codes\include
python pdf_to_markdown.py --input "G:\path\to\pdfs" --output-root ".\outputs\mkd"
```

默认不启用 OCR。如需 OCR：

```powershell
python pdf_to_markdown.py --input "G:\path\to\pdfs" --output-root ".\outputs\mkd" --ocr
```

## Step 1/2/3：GPT-5.4 单模型判断

PDF 输入会自动先转 Markdown：

```powershell
python external_validation_screen.py --input "G:\path\to\pdfs" --provider openai --model gpt-5.4 --task-name cataract --mkd-root ".\outputs\mkd" --output-dir ".\outputs"
```

如果已经有 Markdown：

```powershell
python external_validation_screen.py --input ".\outputs\mkd" --input-type markdown --provider openai --model gpt-5.4 --task-name cataract --output-dir ".\outputs"
```

默认从 `OPENAI_API_KEY` 读取 API key。输出：

```text
outputs\cataract_openai_judgement.jsonl
outputs\cataract_openai_judgement.csv
```

## Step 1/2/3：Qwen3-VL 单模型判断

```powershell
python external_validation_screen.py --input "G:\path\to\pdfs" --provider qwen --model qwen3-vl-plus --task-name cataract --mkd-root ".\outputs\mkd" --output-dir ".\outputs"
```

默认从 `QWEN_API_KEY` 读取 API key。Qwen Step 2 的图片输入使用 DashScope 多模态接口和临时 OSS 上传。

输出：

```text
outputs\cataract_qwen_judgement.jsonl
outputs\cataract_qwen_judgement.csv
```

## 本地冒烟测试

不调用 API，只验证 PDF 转换、Markdown 读取、图片发现和输出路径：

```powershell
python external_validation_screen.py --input "G:\path\to\one.pdf" --provider openai --model gpt-5.4 --task-name test_one --mkd-root ".\outputs\mkd" --limit 1 --dry-run
```

如果只想临时跳过 Step 3，可使用：

```powershell
python external_validation_screen.py --input ".\outputs\mkd" --input-type markdown --provider openai --task-name test_one --skip-judgement
```

## 比较 GPT 与 Qwen 判断

```powershell
python compare_results.py --left ".\outputs\cataract_openai_judgement.csv" --right ".\outputs\cataract_qwen_judgement.csv" --left-name GPT --right-name Qwen --output-dir ".\comparison_results"
```

输出：

- `*_comparison.csv`：所有研究的双模型并排判断。
- `*_needs_debate.csv`：不一致或 unclear 的研究。
- `*_manual_review.csv`：任一模型判断 Yes 或 unclear 的研究。

## Debate / Adjudication

默认只处理不一致或 unclear 的记录；一致 `No/No` 会自动跳过：

```powershell
python debate_judgement.py --left ".\outputs\cataract_openai_judgement.jsonl" --right ".\outputs\cataract_qwen_judgement.jsonl" --left-name GPT --right-name Qwen --task-name cataract --provider openai --model gpt-5.4 --source-dir ".\outputs\mkd" --output-dir ".\debate_results"
```

输出：

```text
debate_results\cataract_debate_judgement.jsonl
debate_results\cataract_debate_judgement.csv
debate_results\cataract_manual_review_after_debate.csv
```

`cataract_manual_review_after_debate.csv` 会保留 GPT、Qwen 或 debate 中至少一个为 Yes/unclear 的记录。

## 注意事项

- PDF 转换依赖 `docling`，首次运行可能较慢。
- Qwen 图片输入依赖 `dashscope` 和 `requests`。
- 本阶段会读取全文并调用模型 API，可能产生费用。
- `external_validation=No` 且 GPT/Qwen 一致时不会进入 debate，也不会进入人工判断清单。
