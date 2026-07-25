"""OpenAI batch client used by the title/abstract screening pipeline."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

from openai import OpenAI


class BatchScreeningClient:
    """Submit title/abstract screening prompts through the OpenAI Batch API."""

    def __init__(
        self,
        api_key: str,
        job_dir: str | Path,
        result_dir: str | Path,
        task_name: str,
        model: str = "gpt-5.1",
    ) -> None:
        self.client = OpenAI(api_key=api_key)
        self.job_dir = Path(job_dir)
        self.result_dir = Path(result_dir)
        self.task_name = task_name
        self.model = model

        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.job_dir / f"{task_name}_title_abstract_jobs.jsonl"
        self.results_file = self.result_dir / f"{task_name}_title_abstract_results.jsonl"

    def screen_texts(self, system_prompt: str, user_prompts: Iterable[str]) -> list[str]:
        self._write_jobs(system_prompt, user_prompts)
        batch_input_id = self._upload_jsonl(self.jobs_file)
        batch_id = self.client.batches.create(
            input_file_id=batch_input_id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
        ).id
        output_file_id = self._wait_for_batch(batch_id)
        self._download_results(output_file_id, self.results_file)
        return self._read_batch_messages(self.results_file)

    def _write_jobs(self, system_prompt: str, user_prompts: Iterable[str]) -> None:
        with self.jobs_file.open("w", encoding="utf-8") as f:
            for i, user_prompt in enumerate(user_prompts):
                job = {
                    "custom_id": f"title_abstract::{i}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                }
                f.write(json.dumps(job, ensure_ascii=False) + "\n")
        print(f"Job file prepared: {self.jobs_file}")

    def _upload_jsonl(self, path: Path) -> str:
        with path.open("rb") as f:
            return self.client.files.create(file=f, purpose="batch").id

    def _wait_for_batch(self, batch_id: str) -> str:
        while True:
            batch = self.client.batches.retrieve(batch_id)
            print(f"Batch status: {batch.status}")
            if batch.status == "completed":
                if not batch.output_file_id:
                    raise RuntimeError(f"Batch {batch_id} completed without output_file_id")
                return batch.output_file_id
            if batch.status in {"failed", "cancelled", "expired"}:
                raise RuntimeError(f"Batch {batch_id} ended with status: {batch.status}")
            time.sleep(15)

    def _download_results(self, file_id: str, save_as: Path) -> None:
        content = self.client.files.content(file_id).text
        save_as.write_text(content, encoding="utf-8")
        print(f"Results saved to: {save_as}")

    @staticmethod
    def _read_batch_messages(path: Path) -> list[str]:
        messages: list[str] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                messages.append(obj["response"]["body"]["choices"][0]["message"]["content"])
        return messages
