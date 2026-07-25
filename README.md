# Eye-AI External Review

Code and prompt tables for title/abstract screening and full-text external-validation identification in ophthalmic AI systematic review workflows.

## Repository Structure

- `code/`: runnable scripts.
- `prompts/`: prompt tables. The prompt contents are stored in spreadsheet files and are not duplicated as Python prompt files.
- `public_information/`: public release materials. These files will be added later.

## Modules

- `code/Screen/`: title and abstract four-step screening code.
- `code/external_validation_identification/`: PDF-to-Markdown conversion, GPT/Qwen external-validation judgement, comparison, debate, and manual-review routing code.
- `prompts/screen_prompts.xlsx`: title/abstract screening prompts.
- `prompts/external_prompts.xlsx`: external-validation identification prompts.
- `prompts/debate_prompts.xlsx`: debate/adjudication prompt.

## Prompt Handling

The runnable scripts only contain prompt placeholders. Before production use, insert or connect the approved prompts from the spreadsheet files in `prompts/`. The spreadsheet files are preserved as the source of prompt text.

## Secrets

Copy `public_information/.env.example` to `.env` in the repository root and fill in your own API keys. Do not commit `.env`.

## Public Information

Public information files are not included yet. They will be released later in `public_information/`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
