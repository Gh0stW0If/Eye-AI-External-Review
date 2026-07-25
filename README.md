# Eye-AI External Review

Code, prompt tables, and public information for title/abstract screening and full-text external-validation identification in ophthalmic AI systematic review workflows.

## Repository Structure

- `code/`: runnable scripts.
- `prompts/`: prompt tables. The prompt contents are stored in spreadsheet files and are not duplicated as Python prompt files.
- `public_information/`: public release materials, including the included-paper list and human gold-standard sensitivity-analysis files.

## Modules

- `code/Screen/`: title and abstract four-step screening code.
- `code/external_validation_identification/`: PDF-to-Markdown conversion, GPT/Qwen external-validation judgement, comparison, debate, and manual-review routing code.
- `prompts/screen_prompts.xlsx`: title/abstract screening prompts.
- `prompts/external_prompts.xlsx`: external-validation identification prompts.
- `prompts/debate_prompts.xlsx`: debate/adjudication prompt.

## Public Information

- `public_information/includeList.xlsx`: list of 2,515 included articles with ID, title, and DOI.
- `public_information/sensitivity analysis/screen_analysis.xlsx`: human gold-standard sensitivity-analysis file for the Screen stage, 600 records.
- `public_information/sensitivity analysis/external_identification.xlsx`: human gold-standard sensitivity-analysis file for the external-validation-identification stage, 457 records.

## Prompt Handling

The runnable scripts only contain prompt placeholders. Before production use, insert or connect the approved prompts from the spreadsheet files in `prompts/`. The spreadsheet files are preserved as the source of prompt text.

## Secrets

Copy `public_information/.env.example` to `.env` in the repository root and fill in your own API keys. Do not commit `.env`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
