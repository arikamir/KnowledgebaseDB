"""Procedure-only departed-owner retention processing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import text

from storage.database import DatabaseManager


@dataclass(frozen=True, slots=True)
class RetentionProcedureResult:
    action_id: str
    status: str


class RetentionProcedures(Protocol):
    """The only database capability granted to the retention workload."""

    def claim_and_process_due(self, now: datetime) -> RetentionProcedureResult | None: ...


@dataclass(slots=True)
class PostgresRetentionProcedures:
    """Invoke SECURITY DEFINER procedures without direct table access."""

    database: DatabaseManager

    def claim_and_process_due(self, now: datetime) -> RetentionProcedureResult | None:
        # Claim and purge share one transaction: a process loss rolls the claim
        # back to pending rather than stranding an owner in `running`.
        with self.database.session() as session:
            claimed = session.execute(
                text("SELECT action_id, action_status FROM claim_due_retention_action(:now)"),
                {"now": now},
            ).mappings().one_or_none()
            if claimed is None:
                return None
            row = session.execute(
                text("SELECT action_id, action_status FROM process_retention_action(:action_id, :now)"),
                {"action_id": claimed["action_id"], "now": now},
            ).mappings().one()
        return RetentionProcedureResult(row["action_id"], row["action_status"])


@dataclass(slots=True)
class RetentionProcessor:
    procedures: RetentionProcedures
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def process_available(self, *, limit: int = 100) -> list[RetentionProcedureResult]:
        """Drain due actions, including overdue rows discovered after restore."""
        if limit < 1:
            raise ValueError("limit must be positive")
        completed: list[RetentionProcedureResult] = []
        for _ in range(limit):
            current = self.now()
            result = self.procedures.claim_and_process_due(current)
            if result is None:
                break
            if result.status != "completed":
                raise RuntimeError("RETENTION_PROCEDURE_RESULT_INVALID")
            completed.append(result)
        return completed

    def restore_catch_up(self, *, batch_limit: int = 100) -> list[RetentionProcedureResult]:
        return self.process_available(limit=batch_limit)


def main() -> None:
    raise SystemExit("Runtime database wiring requires the retention workload's procedure-only Entra identity.")


if __name__ == "__main__":
    main()
