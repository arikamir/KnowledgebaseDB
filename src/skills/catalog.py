"""Extensible skill catalog loader and lookup helpers."""

from __future__ import annotations

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from difflib import get_close_matches

from agent.errors import ConfigurationError
from agent.settings import AppSettings
from knowledge.schemas import SkillArea


def _normalize_key(value: str) -> str:
    return "".join(ch for ch in value.lower().strip() if ch.isalnum() or ch.isspace()).split()


def _normalize_text(value: str) -> str:
    return " ".join(_normalize_key(value))


@dataclass(slots=True)
class SkillCatalog:
    topics: list[SkillArea] = field(default_factory=list)
    _by_name: dict[str, SkillArea] = field(init=False, default_factory=dict)
    _by_alias: dict[str, SkillArea] = field(init=False, default_factory=dict)
    _search_index: list[str] = field(init=False, default_factory=list)
    catalog_version: str = "legacy"
    _states: dict[str, str] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._by_name = {}
        self._by_alias = {}
        self._search_index = []
        self._states = getattr(self, "_states", {})

        for topic in self.topics:
            self._by_name[_normalize_text(topic.name)] = topic
            self._search_index.append(_normalize_text(topic.name))
            for alias in topic.aliases:
                self._by_alias[_normalize_text(alias)] = topic
                self._search_index.append(_normalize_text(alias))

    @classmethod
    def load(cls, source: str | Path | None = None) -> "SkillCatalog":
        if source is None:
            source = Path(__file__).resolve().parents[1] / "knowledge" / "topics" / "topics.json"

        path = Path(source)
        if path.is_dir():
            path = path / "topics.json"

        if path.exists() and path.suffix in {".yaml", ".yml"}:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            source_topics = json.loads((path.parents[1] / document["source_snapshot"]).read_text(encoding="utf-8")) if not Path(document["source_snapshot"]).is_absolute() else json.loads(Path(document["source_snapshot"]).read_text())
            details = {item["name"]: item for item in source_topics}
            raw = []
            states = {}
            for item in document["topics"]:
                enriched = dict(details.get(item["name"], {}))
                enriched.update({"name": item["name"], "category": item["category"], "aliases": item["aliases"], "is_active": item["status"] == "active"})
                raw.append(enriched)
                states[_normalize_text(item["id"])] = item["status"]
                states[_normalize_text(item["name"])] = item["status"]
                for alias in item["aliases"]:
                    states[_normalize_text(alias)] = item["status"]
            catalog = cls(topics=[SkillArea.model_validate(item) for item in raw], catalog_version=document["catalog_version"])
            catalog._states = states
            return catalog
        elif path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
        else:
            raise ConfigurationError(f"Skill catalog file not found: {path}")

        topics = [SkillArea.model_validate(item) for item in raw]
        if not topics:
            raise ConfigurationError("Skill catalog is empty")
        return cls(topics=topics)

    def topic_state(self, name: str) -> str | None:
        return self._states.get(_normalize_text(name)) or ("active" if self.get_active(name) else None)

    def active_topics(self) -> list[SkillArea]:
        return [topic for topic in self.topics if topic.is_active]

    def all_topics(self) -> list[SkillArea]:
        return list(self.topics)

    def topic_names(self, include_inactive: bool = False) -> list[str]:
        topics = self.topics if include_inactive else self.active_topics()
        return [topic.name for topic in topics]

    def get(self, name: str) -> SkillArea | None:
        normalized = _normalize_text(name)
        return self._by_name.get(normalized) or self._by_alias.get(normalized)

    def get_active(self, name: str) -> SkillArea | None:
        topic = self.get(name)
        if topic and topic.is_active:
            return topic
        return None

    def inactive_match(self, name: str) -> SkillArea | None:
        topic = self.get(name)
        if topic and not topic.is_active:
            return topic
        return None

    def suggest(self, name: str, limit: int = 3) -> list[str]:
        normalized = _normalize_text(name)
        matches = get_close_matches(normalized, self._search_index, n=limit * 2, cutoff=0.35)
        suggestions: list[str] = []
        for match in matches:
            topic = self._by_name.get(match) or self._by_alias.get(match)
            if topic and topic.is_active and topic.name not in suggestions:
                suggestions.append(topic.name)
            if len(suggestions) >= limit:
                break
        return suggestions

    def related_topics(self, name: str, limit: int = 3) -> list[str]:
        topic = self.get(name)
        if not topic:
            return self.suggest(name, limit=limit)
        related: list[str] = []
        for related_name in topic.related_skills:
            related_topic = self.get_active(related_name)
            if related_topic and related_topic.name not in related:
                related.append(related_topic.name)
            if len(related) >= limit:
                break
        if len(related) < limit:
            for suggestion in self.suggest(name, limit=limit):
                if suggestion not in related:
                    related.append(suggestion)
                if len(related) >= limit:
                    break
        return related


def load_default_catalog(settings: AppSettings | None = None) -> SkillCatalog:
    source = settings.topic_catalog_path if settings else None
    return SkillCatalog.load(source)
