"""Add versioned lab policy, reference, report, and validation persistence."""

from alembic import op

from storage.database import Base
import storage.lab_models  # noqa: F401


revision = "005_lab_references"
down_revision = "004_identity_lifecycle_idempotency"
branch_labels = None
depends_on = None

TABLES = (
    "lab_provider_approvals",
    "hands_on_lab_references",
    "lab_link_reports",
    "lab_validation_attempts",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    op.execute(
        "INSERT INTO retention_relationship_registry "
        "(table_name, owner_column, registered_revision) VALUES "
        "('lab_link_reports', 'employee_identity_id', '005_lab_references')"
    )
    if bind.dialect.name == "postgresql":
        op.execute("""
        CREATE OR REPLACE FUNCTION reject_lab_report_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
          IF TG_OP='DELETE' AND current_user=(SELECT tableowner FROM pg_tables WHERE schemaname='public' AND tablename='lab_link_reports') THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION 'LAB_REPORT_APPEND_ONLY';
        END $$;
        CREATE TRIGGER lab_report_no_update BEFORE UPDATE OR DELETE ON lab_link_reports
        FOR EACH ROW EXECUTE FUNCTION reject_lab_report_mutation();
        CREATE OR REPLACE FUNCTION reject_lab_validation_history_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'LAB_VALIDATION_HISTORY_APPEND_ONLY'; END $$;
        CREATE TRIGGER lab_validation_no_update BEFORE UPDATE OR DELETE ON lab_validation_attempts
        FOR EACH ROW EXECUTE FUNCTION reject_lab_validation_history_mutation();
        """)
        op.execute("""
        CREATE OR REPLACE FUNCTION enforce_retired_lab_immutability() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
          IF OLD.availability_state='retired' AND NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION 'RETIRED_LAB_VERSION_IMMUTABLE';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER retired_lab_no_update BEFORE UPDATE ON hands_on_lab_references
        FOR EACH ROW EXECUTE FUNCTION enforce_retired_lab_immutability();
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS reject_lab_report_mutation() CASCADE")
        op.execute("DROP FUNCTION IF EXISTS reject_lab_validation_history_mutation() CASCADE")
        op.execute("DROP FUNCTION IF EXISTS enforce_retired_lab_immutability() CASCADE")
    op.execute("DELETE FROM retention_relationship_registry WHERE registered_revision='005_lab_references'")
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
