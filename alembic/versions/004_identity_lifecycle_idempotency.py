"""Identity lifecycle, outbox, retention, and idempotency foundation."""

from alembic import op
import sqlalchemy as sa

revision = "004_identity_lifecycle_idempotency"
down_revision = "003_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("employee_identities", sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False), sa.Column("object_id", sa.String(64), nullable=False), sa.Column("display_name", sa.String(256), nullable=False), sa.Column("employee_profile_id", sa.String(64)), sa.Column("lifecycle_status", sa.String(16), nullable=False), sa.Column("directory_state", sa.String(16), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("lifecycle_checked_at", sa.DateTime(timezone=True)), sa.Column("departed_at", sa.DateTime(timezone=True)), sa.Column("access_blocked_at", sa.DateTime(timezone=True)), sa.Column("retention_due_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("tenant_id", "object_id", name="uq_employee_identity_subject"))
    op.create_table("machine_principals", sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False), sa.Column("client_id", sa.String(64), nullable=False), sa.Column("display_name", sa.String(256), nullable=False), sa.Column("allowed_roles", sa.JSON(), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("tenant_id", "client_id", name="uq_machine_principal_client"))
    op.create_table("directory_reconciliation_runs", sa.Column("id", sa.String(64), primary_key=True), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("checkpoint", sa.String(1024)), sa.Column("status", sa.String(32), nullable=False), sa.Column("checked_count", sa.Integer(), nullable=False), sa.Column("departed_count", sa.Integer(), nullable=False), sa.Column("error_count", sa.Integer(), nullable=False), sa.Column("last_error_code", sa.String(64)))
    op.create_table("retention_actions", sa.Column("id", sa.String(64), primary_key=True), sa.Column("employee_identity_id", sa.String(64), sa.ForeignKey("employee_identities.id", ondelete="SET NULL")), sa.Column("due_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("status", sa.String(32), nullable=False), sa.Column("operation", sa.String(64), nullable=False), sa.Column("evidence_disposition", sa.String(32), nullable=False), sa.Column("attempt_count", sa.Integer(), nullable=False), sa.Column("last_error_code", sa.String(64)), sa.Column("aggregate_counts", sa.JSON(), nullable=False), sa.UniqueConstraint("employee_identity_id", "operation", name="uq_retention_owner_operation"), sa.CheckConstraint("status != 'completed' OR employee_identity_id IS NULL", name="ck_completed_retention_unlinked"))
    op.create_table("session_revocation_outbox", sa.Column("id", sa.String(64), primary_key=True), sa.Column("reconciliation_run_id", sa.String(64), sa.ForeignKey("directory_reconciliation_runs.id"), nullable=False), sa.Column("employee_identity_id", sa.String(64), sa.ForeignKey("employee_identities.id", ondelete="CASCADE"), nullable=False), sa.Column("tenant_id", sa.String(64), nullable=False), sa.Column("object_id", sa.String(64), nullable=False), sa.Column("departed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("attempt_count", sa.Integer(), nullable=False), sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_attempt_at", sa.DateTime(timezone=True)), sa.Column("acknowledged_at", sa.DateTime(timezone=True)), sa.Column("last_error_code", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("reconciliation_run_id", "employee_identity_id", name="uq_revocation_run_owner"))
    op.create_index("ix_revocation_dispatch", "session_revocation_outbox", ["status", "next_attempt_at"])
    op.create_table("idempotency_records", sa.Column("id", sa.String(64), primary_key=True), sa.Column("actor_type", sa.String(16), nullable=False), sa.Column("actor_id", sa.String(64), nullable=False), sa.Column("operation", sa.String(128), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("canonical_request_hash", sa.String(64), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("response_status", sa.Integer()), sa.Column("response_body", sa.JSON()), sa.Column("resource_reference", sa.String(256)), sa.Column("attempt_count", sa.Integer(), nullable=False), sa.Column("execution_lease_expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False), sa.Column("retry_after", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("response_expires_at", sa.DateTime(timezone=True)), sa.Column("tombstoned_at", sa.DateTime(timezone=True)), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("principal_revoked_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("actor_type", "actor_id", "operation", "idempotency_key", name="uq_idempotency_scope"), sa.CheckConstraint("actor_type IN ('employee','application')", name="ck_idempotency_actor_type"), sa.CheckConstraint("status IN ('processing','succeeded','retryable_failed','final_failed')", name="ck_idempotency_status"), sa.CheckConstraint("execution_lease_expires_at > last_heartbeat_at", name="ck_idempotency_lease_after_heartbeat"), sa.CheckConstraint("status NOT IN ('processing','retryable_failed') OR expires_at IS NULL", name="ck_live_idempotency_not_expiring"), sa.CheckConstraint("status NOT IN ('succeeded','final_failed') OR response_status IS NOT NULL", name="ck_terminal_idempotency_has_status"))
    op.create_index("ix_idempotency_records_actor_id", "idempotency_records", ["actor_id"])
    # PostgreSQL deployments add SECURITY DEFINER claim/process procedures and
    # least-privilege grants in the environment-specific migration runner.
    op.create_table("retention_relationship_registry", sa.Column("table_name", sa.String(128), primary_key=True), sa.Column("owner_column", sa.String(128), nullable=False), sa.Column("registered_revision", sa.String(64), nullable=False))
    op.execute("INSERT INTO retention_relationship_registry (table_name, owner_column, registered_revision) VALUES ('idempotency_records', 'actor_id', '004_identity_lifecycle_idempotency')")
    op.execute("INSERT INTO retention_relationship_registry (table_name, owner_column, registered_revision) VALUES ('session_revocation_outbox', 'employee_identity_id', '004_identity_lifecycle_idempotency')")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE OR REPLACE FUNCTION claim_due_retention_action(p_now timestamptz)
        RETURNS TABLE(action_id varchar, action_status varchar)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        BEGIN
          RETURN QUERY
          WITH candidate AS (
            SELECT id FROM retention_actions
            WHERE status IN ('pending','retryable_failed')
              AND due_at <= p_now AND employee_identity_id IS NOT NULL
            ORDER BY due_at, id FOR UPDATE SKIP LOCKED LIMIT 1
          )
          UPDATE retention_actions r
             SET status='running', attempt_count=attempt_count+1
            FROM candidate c WHERE r.id=c.id
          RETURNING r.id, r.status;
        END $$;
        REVOKE ALL ON FUNCTION claim_due_retention_action(timestamptz) FROM PUBLIC;
        """)
        op.execute("""
        CREATE OR REPLACE FUNCTION process_retention_action(p_action_id varchar, p_now timestamptz)
        RETURNS TABLE(action_id varchar, action_status varchar)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        DECLARE owner_id varchar; deleted_outbox integer := 0; deleted_idempotency integer := 0;
        BEGIN
          SELECT employee_identity_id INTO owner_id FROM retention_actions
           WHERE id=p_action_id AND status='running' AND due_at <= p_now FOR UPDATE;
          IF owner_id IS NULL THEN RAISE EXCEPTION 'RETENTION_ACTION_INELIGIBLE'; END IF;
          DELETE FROM session_revocation_outbox WHERE employee_identity_id=owner_id;
          GET DIAGNOSTICS deleted_outbox = ROW_COUNT;
          DELETE FROM idempotency_records WHERE actor_type='employee' AND actor_id=owner_id;
          GET DIAGNOSTICS deleted_idempotency = ROW_COUNT;
          DELETE FROM employee_identities WHERE id=owner_id;
          UPDATE retention_actions SET employee_identity_id=NULL, status='completed', completed_at=p_now,
            aggregate_counts=jsonb_build_object('outbox',deleted_outbox,'idempotency',deleted_idempotency)
            WHERE id=p_action_id;
          RETURN QUERY SELECT p_action_id, 'completed'::varchar;
        END $$;
        REVOKE ALL ON FUNCTION process_retention_action(varchar,timestamptz) FROM PUBLIC;
        """)


def downgrade() -> None:
    for table in ("retention_relationship_registry", "idempotency_records", "session_revocation_outbox", "retention_actions", "directory_reconciliation_runs", "machine_principals", "employee_identities"):
        op.drop_table(table)
