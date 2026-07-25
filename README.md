# Eye-AI External Review

Code and prompts for title/abstract screening and full-text external-validation review in ophthalmic AI systematic review workflows.

## Repository Structure

- `code/`: runnable screening and external-validation scripts.
- `prompts/`: prompt templates used by the screening and full-text review workflows.
- `public_information/`: public release materials. These files will be added later.

## Modules

- `code/Screen/`: title and abstract four-step screening.
- `code/include/`: PDF-to-Markdown conversion, GPT/Qwen external-validation judgement, comparison, debate, and manual-review routing.
- `prompts/Screen/`: prompts for title/abstract screening.
- `prompts/include/`: prompts for full-text external-validation review.

## Secrets

Copy `public_information/.env.example` to `.env` in the repository root and fill in your own API keys. Do not commit `.env`.

## Public Information

Public information files are not included yet. They will be released later in `public_information/`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
