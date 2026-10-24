"""Amazon Bedrock labeler for notes the rules cannot decide. Never required to run."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from data_pipeline.labeler import LABELS

log = logging.getLogger(__name__)
PROMPT_PATH: Path = Path(__file__).with_name("label_prompt.txt")
MAX_CONSECUTIVE_ERRORS = 3


def fallback_enabled() -> bool:
    """True when DRAINFAST_FALLBACK=1, meaning no AI calls at all."""
    return os.environ.get("DRAINFAST_FALLBACK", "").strip() == "1"


def parse_answer(text: str) -> str | None:
    """Return the label when the model answered exactly one valid label, else None."""
    cleaned = text.strip().strip("`'\".: \n").lower()
    return cleaned if cleaned in LABELS else None


class BedrockLabeler:
    """Labels undecided notes with the Bedrock Converse API, with a JSON answer cache."""

    def __init__(self, model_id: str, cache_path: Path, client: Any | None = None) -> None:
        self.model_id = model_id
        self.cache_path = Path(cache_path)
        self.prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.cache: dict[str, str] = self._load_cache()
        self._client = client
        self._errors = 0
        self.calls = 0

    def _load_cache(self) -> dict[str, str]:
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("LLM cache unreadable, starting empty: %s", self.cache_path)
            return {}
        return {k: v for k, v in data.items() if v in LABELS}

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3

            session = boto3.Session(
                profile_name=os.environ.get("AWS_PROFILE") or None,
                region_name=os.environ.get("AWS_REGION") or None,
            )
            self._client = session.client("bedrock-runtime")
        return self._client

    def label(self, note: str) -> str | None:
        """Return a valid label for the note, or None on any problem."""
        if note in self.cache:
            return self.cache[note]
        if self._errors >= MAX_CONSECUTIVE_ERRORS:
            return None
        try:
            self.calls += 1
            response = self._get_client().converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": self.prompt.format(note=note)}]}],
                inferenceConfig={"maxTokens": 10, "temperature": 0.0},
            )
            text = response["output"]["message"]["content"][0]["text"]
        except Exception as exc:  # network, auth, throttling, bad response shape
            self._errors += 1
            log.warning("Bedrock call failed (%s/%s): %s", self._errors, MAX_CONSECUTIVE_ERRORS, exc)
            if self._errors >= MAX_CONSECUTIVE_ERRORS:
                log.warning("Bedrock disabled for the rest of this run; notes stay unclear.")
            return None
        self._errors = 0
        answer = parse_answer(text)
        if answer is not None:
            self.cache[note] = answer
        return answer

    def save_cache(self) -> None:
        """Write the answer cache to disk, sorted for stable diffs."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(dict(sorted(self.cache.items())), indent=1), encoding="utf-8")


def make_labeler(cache_path: Path) -> BedrockLabeler | None:
    """Return a Bedrock labeler, or None in fallback mode or without BEDROCK_MODEL_ID."""
    if fallback_enabled():
        log.info("DRAINFAST_FALLBACK=1: no Bedrock calls; undecided notes stay unclear.")
        return None
    model_id = os.environ.get("BEDROCK_MODEL_ID", "").strip()
    if not model_id:
        log.info("BEDROCK_MODEL_ID not set: no Bedrock calls; undecided notes stay unclear.")
        return None
    return BedrockLabeler(model_id, cache_path)
