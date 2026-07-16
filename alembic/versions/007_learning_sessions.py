"""Add the sibling learning-session persistence head."""

from alembic import op

from storage.database import Base
import storage.learning_models  # noqa: F401

revision = "007_learning_sessions"
down_revision = "006_owned_roadmaps"
branch_labels = ("learning",)
depends_on = None

TABLES = (
    "learning_content", "learning_steps", "review_questions", "employee_learning_sessions",
    "learning_step_progress", "learning_lab_state", "learning_lab_reports", "review_attempts", "review_answers",
    "learning_milestone_completions", "learning_required_clock_segments", "learning_activity_events",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    op.execute("INSERT INTO retention_relationship_registry (table_name, owner_column, registered_revision) VALUES ('employee_learning_sessions', 'employee_identity_id', '007_learning_sessions')")
    op.execute("INSERT INTO retention_relationship_registry (table_name, owner_column, registered_revision) VALUES ('learning_milestone_completions', 'employee_identity_id', '007_learning_sessions')")
    op.execute("INSERT INTO retention_relationship_registry (table_name, owner_column, registered_revision) VALUES ('learning_activity_events', 'employee_identity_id', '007_learning_sessions')")


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
