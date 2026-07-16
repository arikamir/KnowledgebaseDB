from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[2] / "alembic/versions/004_identity_lifecycle_idempotency.py"


def test_retention_procedures_are_security_definer_and_public_is_revoked() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    for function in ("claim_due_retention_action", "process_retention_action"):
        assert f"FUNCTION {function}" in source
        assert f"REVOKE ALL ON FUNCTION {function}" in source
    assert source.count("LANGUAGE plpgsql SECURITY DEFINER") == 2
    assert "FOR UPDATE SKIP LOCKED" in source
    assert "employee_identity_id=NULL" in source
