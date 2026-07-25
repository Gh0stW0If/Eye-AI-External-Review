# Title and Abstract Screening

This module performs a four-step title/abstract screening workflow for ophthalmic AI literature review projects. The default model is `gpt-5.4`.

## Four-Step Screening Logic

1. `Response1`: determine whether the article matches the target disease area and uses an AI method.
2. `Response2`: exclude ineligible article types or study designs, such as reviews, meta-analyses, conference abstracts, animal studies, basic research, and secondary research.
3. `Response3`: determine whether the primary task is disease diagnosis, disease classification, prognosis prediction, or risk prediction. Excluded tasks include image quality assessment, segmentation-only tasks, quantitative measurement-only studies, isolated sign detection, treatment planning, surgical assistance, image generation, and dataset construction.
4. `Response4`: determine whether the study directly uses original medical images or videos as model input.

The script automatically stops later steps when an earlier step is negative:

- Step 1 `False`: skip Steps 2-4.
- Step 2 `False`: skip Steps 3-4.
- Step 3 `False`: skip Step 4.

## Files

- `title_abstract_screen.py`: main CLI for reading CSV/Excel files, running the four-step screen, and exporting CSV results.
- `../../prompts/Screen/prompts.py`: prompt templates and disease-specific notes.
- `screening_client.py`: optional OpenAI Batch API helper.
- `requirements.txt`: dependencies.

## Input Format

Input can be a single `.csv`, `.xlsx`, or `.xls` file, or a folder containing these files.

Required columns:

- Title: `Title`, `TITLE`, or `title`
- Abstract: `Abstract`, `ABSTRACT`, or `abstract`

## Usage

```powershell
cd code\Screen
python title_abstract_screen.py --input ".\examples\papers.csv" --disease cataract
```

Specify an output directory:

```powershell
python title_abstract_screen.py --input ".\examples\papers.csv" --output-dir ".\outputs" --disease cataract
```

Resume from existing decision columns:

```powershell
python title_abstract_screen.py --input ".\outputs\papers_step1and2.csv" --disease cataract --resume
```

Default output suffix is `step3and4`. For example, `papers.csv` becomes `papersstep3and4.csv`.

Custom suffix:

```powershell
python title_abstract_screen.py --input ".\examples\papers.csv" --output-suffix "screened"
```

## Disease Keys

`--disease` supports:

- `cataract`
- `amd`
- `glaucoma`
- `drdme`
- `rop`
- `ocularsurface`
- `oculomics`

Use `--disease-text` to provide a custom disease description for Step 1.

## Step 4 Mode

`--step4-kind` supports:

- `video`: default; allows original medical images or video frames.
- `standard`: original medical images only.
- `anterior`: anterior-segment imaging, such as AS-OCT, UBM, slit-lamp photographs, anterior-segment photographs, or gonioscopy.

## Output Columns

The output CSV keeps all original columns and appends or updates:

- `Response1`, `Response1_decision`, `Response1_confidence`, `Response1_reason`
- `Response2`, `Response2_decision`, `Response2_confidence`, `Response2_reason`
- `Response3`, `Response3_decision`, `Response3_confidence`, `Response3_reason`
- `Disease_type`, `Main_task`
- `Response4`, `Response4_decision`, `Response4_confidence`, `Response4_reason`

## Not Included In This Stage

The title/abstract screen does not judge:

- non-English articles;
- full-text availability.

These criteria should be handled in later workflow stages or manually.

## API Key

The default model is `gpt-5.4`. The script reads `OPENAI_API_KEY` from the environment and also attempts to load `.env` from the repository root. Use `public_information/.env.example` as the template.

```powershell
python title_abstract_screen.py --input ".\examples\papers.csv" --model "gpt-5.4" --api-key-env "OPENAI_API_KEY"
```

## Dependencies

```powershell
pip install -r requirements.txt
```

## Notes

- Running the script calls model APIs and may incur cost.
- This stage only uses titles and abstracts; it does not read full-text PDFs.
- If JSON parsing fails, the corresponding step records `parse_error` and stores the raw error in the reason column.


