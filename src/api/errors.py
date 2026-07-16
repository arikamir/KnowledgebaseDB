"""Stable RFC 9457-style problem responses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApiProblem(Exception):
    status: int
    code: str
    title: str
    detail: str | None = None
    retry_after: int | None = None

    def body(self, correlation_id: str) -> dict[str, object]:
        body: dict[str, object] = {
            "type": f"https://knowledgebasedb.invalid/problems/{self.code.lower()}",
            "title": self.title,
            "status": self.status,
            "code": self.code,
            "correlationId": correlation_id,
        }
        if self.detail:
            body["detail"] = self.detail
        return body
