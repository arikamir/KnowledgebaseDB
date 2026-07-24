from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_learning_revision_is_a_sibling_head_with_owner_registration() -> None:
    source = (ROOT / "alembic/versions/007_learning_sessions.py").read_text()
    assert 'down_revision = "006_owned_roadmaps"' in source
    assert 'branch_labels = ("learning",)' in source
    assert "employee_learning_sessions" in source
    assert "learning_milestone_completions" in source
    assert "retention_relationship_registry" in source
