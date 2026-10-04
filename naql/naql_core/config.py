"""Environment-based configuration (C10: no secrets in code)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_DATA_DIR = "data"


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration loaded from environment variables."""

    data_dir: Path
    llm_provider: str  # "disabled" | "openai_compatible"
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_temperature: float


def load_config() -> AppConfig:
    """Load configuration from environment variables.

    Returns:
        AppConfig populated from NAQL_* environment variables with safe
        defaults; LLM is disabled unless explicitly configured.
    """
    return AppConfig(
        data_dir=Path(os.environ.get("NAQL_DATA_DIR", _DEFAULT_DATA_DIR)),
        llm_provider=os.environ.get("NAQL_LLM_PROVIDER", "disabled"),
        llm_base_url=os.environ.get("NAQL_LLM_BASE_URL", ""),
        llm_api_key=os.environ.get("NAQL_LLM_API_KEY", ""),
        llm_model=os.environ.get("NAQL_LLM_MODEL", ""),
        llm_temperature=float(os.environ.get("NAQL_LLM_TEMPERATURE", "0.1")),
    )
