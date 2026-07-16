"""Add exactly-owned roadmaps and stable milestones."""

from alembic import op
import sqlalchemy as sa
from storage.roadmap_models import classify_legacy_roadmap

revision = "006_owned_roadmaps"
down_revision = "004_identity_lifecycle_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("owned_roadmaps", sa.Column("id", sa.String(64), primary_key=True), sa.Column("owner_type", sa.String(16), nullable=False), sa.Column("employee_identity_id", sa.String(64), sa.ForeignKey("employee_identities.id", ondelete="CASCADE")), sa.Column("machine_principal_id", sa.String(64), sa.ForeignKey("machine_principals.id", ondelete="CASCADE")), sa.Column("profile_snapshot", sa.JSON(), nullable=False), sa.Column("goal", sa.String(1024), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("ui_contract_state", sa.String(16), nullable=False), sa.Column("content_version", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("(owner_type = 'employee' AND employee_identity_id IS NOT NULL AND machine_principal_id IS NULL) OR (owner_type = 'application' AND machine_principal_id IS NOT NULL AND employee_identity_id IS NULL)", name="ck_roadmap_exact_owner"), sa.UniqueConstraint("employee_identity_id", "id", name="uq_employee_roadmap"), sa.UniqueConstraint("machine_principal_id", "id", name="uq_application_roadmap"))
    op.create_table("roadmap_milestones", sa.Column("roadmap_id", sa.String(64), sa.ForeignKey("owned_roadmaps.id", ondelete="CASCADE"), primary_key=True), sa.Column("milestone_key", sa.String(128), primary_key=True), sa.Column("ordinal", sa.Integer(), nullable=False), sa.Column("title", sa.String(512), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("roadmap_id", "milestone_key", name="uq_roadmap_milestone_key"), sa.UniqueConstraint("roadmap_id", "ordinal", name="uq_roadmap_milestone_ordinal"))
    bind = op.get_bind()
    legacy = sa.table("roadmaps", sa.column("id"), sa.column("employee_profile_id"), sa.column("status"), sa.column("payload"), sa.column("created_at"), sa.column("updated_at"))
    identities = sa.table("employee_identities", sa.column("id"), sa.column("employee_profile_id"))
    owned = sa.table("owned_roadmaps", sa.column("id"), sa.column("owner_type"), sa.column("employee_identity_id"), sa.column("machine_principal_id"), sa.column("profile_snapshot"), sa.column("goal"), sa.column("status"), sa.column("ui_contract_state"), sa.column("content_version"), sa.column("created_at"), sa.column("updated_at"))
    milestone_table = sa.table("roadmap_milestones", sa.column("roadmap_id"), sa.column("milestone_key"), sa.column("ordinal"), sa.column("title"), sa.column("status"), sa.column("created_at"), sa.column("completed_at"))
    identity_by_profile = {row.employee_profile_id: row.id for row in bind.execute(sa.select(identities.c.id, identities.c.employee_profile_id)) if row.employee_profile_id}
    for row in bind.execute(sa.select(legacy)):
        owner_id = identity_by_profile.get(row.employee_profile_id)
        classification, milestones = classify_legacy_roadmap(row.payload, owner_id is not None)
        if owner_id is None:
            continue
        bind.execute(owned.insert().values(id=row.id, owner_type="employee", employee_identity_id=owner_id, machine_principal_id=None, profile_snapshot={"employeeProfileId": row.employee_profile_id}, goal=row.payload.get("goal_summary", "Legacy roadmap"), status=row.status, ui_contract_state=classification, content_version="legacy-v1", created_at=row.created_at, updated_at=row.updated_at))
        for item in milestones:
            bind.execute(milestone_table.insert().values(roadmap_id=row.id, created_at=row.created_at, completed_at=None, **item))
    op.execute("INSERT INTO retention_relationship_registry (table_name, owner_column, registered_revision) VALUES ('owned_roadmaps', 'employee_identity_id', '006_owned_roadmaps')")


def downgrade() -> None:
    op.drop_table("roadmap_milestones")
    op.drop_table("owned_roadmaps")
