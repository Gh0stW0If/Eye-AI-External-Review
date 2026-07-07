# Eye-AI External Review

Code for title/abstract screening and full-text external-validation review in ophthalmic AI systematic review workflows.

## Modules

- `Screen/`: title and abstract four-step screening.
- `include/`: PDF-to-Markdown conversion, GPT/Qwen external-validation judgement, comparison, debate, and manual-review routing.

## Secrets

Copy `.env.example` to `.env` locally and fill in your own API keys. Do not commit `.env`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
