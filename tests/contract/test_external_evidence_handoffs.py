from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_t194_verification_handoff_is_explicitly_pending_and_complete_in_scope() -> None:
    text = (ROOT / "specs/003-develop-ui/verification.md").read_text()
    assert "awaiting authorized Platform Operations execution" in text
    assert "T194 outcome: **not executed**" in text
    for required in (
        "Terraform apply/import", "ALB Controller", "Migration admission", "Every T176 identity",
        "retired CI controller", "T180", "T182", "T193", "T156", "PostgreSQL PITR",
        "Redis session loss", "Immutable evidence zero-RPO", "monthly-close dry run",
    ):
        assert required.casefold() in text.casefold()
    assert "T154 remains blocked" in text


def test_t198_handoff_prohibits_fake_or_replaced_rows_and_has_exact_thresholds() -> None:
    text = (ROOT / "specs/003-develop-ui/usability-results.md").read_text()
    assert "awaiting Product/UX Research execution and sign-off" in text
    assert "No measured rows have been collected" in text
    assert "may not be replaced" in text
    for criterion in ("SC-001", "SC-007", "SC-011", "SC-015", "SC-016", "SC-017"):
        assert criterion in text
    assert "P01" in text and "1/1" in text
    assert "Product/UX Research owner: not signed" in text
