from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lifecycle.retention import RetentionProcedureResult, RetentionProcessor


NOW = datetime(2026, 7, 17, 10, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


class ProcedureHarness:
    """Transaction-shaped stand-in for the PostgreSQL SECURITY DEFINER boundary."""

    def __init__(self, *, departed_at=NOW - timedelta(days=90), due_at=NOW, crash=False):
        self.departed_at = departed_at
        self.due_at = due_at
        self.status = "pending"
        self.owner = "employee-secret"
        self.graph = {
            "profile": ["profile"], "domain": ["roadmap", "learning", "progress"],
            "outbox": ["outbox"], "idempotency": ["key"],
        }
        self.evidence = None
        self.crash = crash
        self.calls = []

    def claim_and_process_due(self, now):
        self.calls.append(("claim", now))
        eligible = (
            self.status in {"pending", "retryable_failed"}
            and self.due_at <= now
            and self.due_at == self.departed_at + timedelta(days=90)
        )
        if not eligible:
            return None
        snapshot = deepcopy((self.status, self.owner, self.graph, self.evidence))
        try:
            self.status = "running"
            action_id = "action-safe"
            self.calls.append(("process", action_id, now))
            if self.status != "running" or self.due_at > now:
                raise RuntimeError("RETENTION_ACTION_INELIGIBLE")
            counts = {name: len(rows) for name, rows in self.graph.items()}
            self.graph = {name: [] for name in self.graph}
            self.owner = None
            if self.crash:
                raise RuntimeError("injected partial purge")
            self.status = "completed"
            self.evidence = counts
            return RetentionProcedureResult(action_id, "completed")
        except Exception:
            self.status, self.owner, self.graph, self.evidence = snapshot
            raise


def test_due_retention_deletes_owner_profile_domain_outbox_and_idempotency_then_unlinks_evidence():
    procedures = ProcedureHarness()
    result = RetentionProcessor(procedures, now=lambda: NOW).process_available()
    assert result == [RetentionProcedureResult("action-safe", "completed")]
    assert procedures.owner is None and all(not rows for rows in procedures.graph.values())
    assert procedures.evidence == {"profile": 1, "domain": 3, "outbox": 1, "idempotency": 1}
    evidence_text = repr(procedures.evidence)
    assert "employee-secret" not in evidence_text and "tenant" not in evidence_text and "object" not in evidence_text


def test_partial_purge_rolls_back_owner_graph_and_unlinking():
    procedures = ProcedureHarness(crash=True)
    original = deepcopy(procedures.graph)
    with pytest.raises(RuntimeError, match="partial purge"):
        RetentionProcessor(procedures, now=lambda: NOW).process_available()
    assert procedures.status == "pending" and procedures.owner == "employee-secret"
    assert procedures.graph == original and procedures.evidence is None


@pytest.mark.parametrize(
    "departed_at,due_at",
    [
        (NOW - timedelta(days=89), NOW),
        (NOW - timedelta(days=90), NOW - timedelta(seconds=1)),
        (NOW - timedelta(days=91), NOW),
    ],
)
def test_eligibility_and_timestamp_tampering_cannot_claim(departed_at, due_at):
    procedures = ProcedureHarness(departed_at=departed_at, due_at=due_at)
    assert RetentionProcessor(procedures, now=lambda: NOW).process_available() == []
    assert procedures.owner == "employee-secret" and procedures.status == "pending"


def test_restore_catch_up_drains_overdue_work_in_bounded_batches():
    procedures = ProcedureHarness(departed_at=NOW - timedelta(days=91), due_at=NOW - timedelta(days=1))
    assert RetentionProcessor(procedures, now=lambda: NOW).restore_catch_up(batch_limit=10)[0].status == "completed"


def test_runtime_uses_only_minimal_procedure_calls_and_migration_owns_the_deletion_matrix():
    runtime = (ROOT / "src/lifecycle/retention.py").read_text()
    assert "claim_due_retention_action" in runtime and "process_retention_action" in runtime
    for forbidden in ("retention_actions", "employee_learning_sessions", "owned_roadmaps", "employee_identities"):
        assert forbidden not in runtime

    migration = (ROOT / "alembic/versions/004_identity_lifecycle_idempotency.py").read_text()
    for table in (
        "progress_reviews", "owned_progress_check_ins", "learning_activity_events",
        "lab_link_reports", "learning_milestone_completions", "employee_learning_sessions", "owned_roadmaps",
        "session_revocation_outbox", "idempotency_records", "progress_check_ins",
        "roadmaps", "employee_profiles", "employee_identities",
    ):
        assert f"DELETE FROM {table}" in migration
    assert "e.retention_due_at=r.due_at" in migration
    assert "e.retention_due_at = e.departed_at + interval '90 days'" in migration
    assert "e.departed_at + interval '90 days' <= p_now" in migration
    assert "employee_identity_id=NULL" in migration
    assert 'ondelete="SET NULL"' in migration
    grants = (ROOT / "infra/azure/data-plane-rbac.tf").read_text()
    assert 'allowed   = ["execute-audited-claim-due", "execute-audited-process-due"]' in grants
    assert "direct-retention-queue-read-write" in grants and "direct-learning-row-read" in grants
    assert "tenant_id" not in migration[migration.index("aggregate_counts=jsonb_build_object"):migration.index("WHERE id=p_action_id", migration.index("aggregate_counts=jsonb_build_object"))]
