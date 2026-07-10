"""Application settings for the DevOps career agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _env_value(source: Mapping[str, str], key: str, default: str) -> str:
    value = source.get(key, default)
    return value.strip() if isinstance(value, str) else default


@dataclass(slots=True)
class AppSettings:
    app_name: str = "DevOps Career Agent"
    environment: str = "development"
    database_url: str = "sqlite:///./devops_career_agent.db"
    log_level: str = "INFO"
    max_clarifying_questions: int = 3
    roadmap_p95_seconds: float = 30.0
    topic_guidance_p95_seconds: float = 10.0
    max_concurrent_employees: int = 10
    topic_catalog_path: str = str(
        Path(__file__).resolve().parents[1] / "knowledge" / "topics" / "topics.json"
    )

    @classmethod
    def load(cls, environ: Mapping[str, str] | None = None) -> "AppSettings":
        source = environ or os.environ
        defaults = cls()
        return cls(
            app_name=_env_value(source, "APP_NAME", defaults.app_name),
            environment=_env_value(source, "ENVIRONMENT", defaults.environment),
            database_url=_env_value(source, "DATABASE_URL", defaults.database_url),
            log_level=_env_value(source, "LOG_LEVEL", defaults.log_level),
            max_clarifying_questions=int(
                _env_value(source, "MAX_CLARIFYING_QUESTIONS", str(defaults.max_clarifying_questions))
            ),
            roadmap_p95_seconds=float(
                _env_value(source, "ROADMAP_P95_SECONDS", str(defaults.roadmap_p95_seconds))
            ),
            topic_guidance_p95_seconds=float(
                _env_value(source, "TOPIC_GUIDANCE_P95_SECONDS", str(defaults.topic_guidance_p95_seconds))
            ),
            max_concurrent_employees=int(
                _env_value(source, "MAX_CONCURRENT_EMPLOYEES", str(defaults.max_concurrent_employees))
            ),
            topic_catalog_path=_env_value(source, "TOPIC_CATALOG_PATH", defaults.topic_catalog_path),
        )


def load_settings(environ: Mapping[str, str] | None = None) -> AppSettings:
    return AppSettings.load(environ=environ)
