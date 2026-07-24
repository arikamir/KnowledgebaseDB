"""Add the sibling actor-owned progress persistence head."""

from alembic import op

from storage.database import Base
import storage.progress_models  # noqa: F401

revision = "008_owned_progress"
down_revision = "006_owned_roadmaps"
branch_labels = ("progress",)
depends_on = None

TABLES = ("owned_progress_check_ins", "progress_reviews")


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    op.execute(
        "INSERT INTO retention_relationship_registry "
        "(table_name, owner_column, registered_revision) VALUES "
        "('owned_progress_check_ins', 'employee_identity_id', '008_owned_progress')"
    )
    op.execute(
        "INSERT INTO retention_relationship_registry "
        "(table_name, owner_column, registered_revision) VALUES "
        "('progress_reviews', 'employee_identity_id', '008_owned_progress')"
    )


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
