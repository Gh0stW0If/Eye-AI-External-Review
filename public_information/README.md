# Public Information

This folder contains public release materials for the Eye-AI External Review project.

## Files

- `includeList.xlsx`: list of 2,515 included articles.
  - `Sheet1`: 2,515 rows.
  - Columns: `ID`, `title`, `DOI`.
- `sensitivity analysis/screen_analysis.xlsx`: human gold-standard sensitivity-analysis file for the title/abstract Screen stage.
  - Sheet: `screen_analysis`.
  - Rows: 600.
  - Columns: `title`, `doi`, `LLM`, `Human`, `agreement`.
- `sensitivity analysis/external_identification.xlsx`: human gold-standard sensitivity-analysis file for the external-validation-identification stage.
  - `Sheet1`: 457 rows.
  - Columns: `No.`, `Title`, `DOI`, `LLM Classification`, `Human Gold-Standard Label`, `Agreement`.

## Notes

- `.env.example` is a local configuration template only. Copy it to the repository root as `.env` and fill in your own API keys.
- Do not commit real API keys or local `.env` files.
