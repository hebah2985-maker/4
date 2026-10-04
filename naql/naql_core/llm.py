"""Swappable LLM client (C3, NFR-09, AI-06).

The ONLY gateway to any LLM. Providers: "disabled" (default, deterministic
fallback) and "openai_compatible" (any OpenAI-compatible HTTP endpoint,
configured purely via environment variables — C10).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from naql_core.config import AppConfig
from naql_core.errors import LlmOutputInvalidError, LlmUnavailableError

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@dataclass(frozen=True)
class Prompt:
    """A versioned system prompt (K5)."""

    version: str
    text: str


def load_prompt(name: str, version: str) -> Prompt:
    """Load a versioned prompt from prompts/ (K5: prompts live only there)."""
    path = _PROMPTS_DIR / f"{name}.{version}.md"
    return Prompt(version=version, text=path.read_text(encoding="utf-8"))


class LLMClient:
    """Single interface to the LLM provider (NFR-09)."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @property
    def model_id(self) -> str:
        """Identifier of the active model (logged with each result, AI-08)."""
        return self._config.llm_model or "disabled"

    def complete_json(self, system: str, user: str) -> dict:
        """Send one chat completion expecting a JSON object reply.

        Args:
            system: System prompt text (from prompts/, versioned).
            user: User message containing ONLY the retrieved paragraphs (AI-01).

        Returns:
            Parsed JSON dict.

        Raises:
            LlmUnavailableError: Provider disabled or unreachable.
            LlmOutputInvalidError: Reply is not valid JSON (E4 caller retries once).
        """
        if self._config.llm_provider != "openai_compatible":
            raise LlmUnavailableError("LLM provider is disabled")
        return self._openai_compatible_json(system, user)

    def _openai_compatible_json(self, system: str, user: str) -> dict:
        """Call an OpenAI-compatible /chat/completions endpoint (C9/C10)."""
        import httpx

        url = f"{self._config.llm_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self._config.llm_model,
            "temperature": self._config.llm_temperature,  # AI-06: low, fixed
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {self._config.llm_api_key}"}
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise LlmUnavailableError("LLM request failed") from exc
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmOutputInvalidError("LLM reply is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise LlmOutputInvalidError("LLM reply is not a JSON object")
        return parsed


class FakeLLMClient:
    """Deterministic test double (T4): fixed outputs, no network."""

    def __init__(self, replies: list[dict] | None = None) -> None:
        self._replies = list(replies or [])
        self.calls = 0

    @property
    def model_id(self) -> str:
        return "fake"

    def complete_json(self, system: str, user: str) -> dict:
        """Return the next scripted reply or raise like a real failure."""
        del system, user
        self.calls += 1
        if not self._replies:
            raise LlmUnavailableError("no scripted reply")
        reply = self._replies.pop(0)
        if reply.get("__invalid__"):
            raise LlmOutputInvalidError("scripted invalid output")
        return reply
