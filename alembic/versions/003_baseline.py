"""Baseline the existing profile, roadmap, and progress tables."""

from alembic import op
import sqlalchemy as sa

revision = "003_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("employee_profiles", sa.Column("id", sa.String(64), primary_key=True), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("roadmaps", sa.Column("id", sa.String(64), primary_key=True), sa.Column("employee_profile_id", sa.String(64), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_roadmaps_employee_profile_id", "roadmaps", ["employee_profile_id"])
    op.create_index("ix_roadmaps_status", "roadmaps", ["status"])
    op.create_table("progress_check_ins", sa.Column("id", sa.String(64), primary_key=True), sa.Column("employee_profile_id", sa.String(64), nullable=False), sa.Column("roadmap_id", sa.String(64), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    op.drop_table("progress_check_ins")
    op.drop_table("roadmaps")
    op.drop_table("employee_profiles")
