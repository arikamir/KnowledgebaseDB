"""Merge the learning and progress story heads for combined releases."""

revision = "009_merge_learning_progress"
down_revision = ("007_learning_sessions", "008_owned_progress")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge-only revision; both expand-only parents contain the schema work."""


def downgrade() -> None:
    """Split only the version graph; parent schema downgrades remain explicit."""
