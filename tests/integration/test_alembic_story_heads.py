from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parents[2]
MERGE_REVISION = "009_merge_learning_progress"
LEARNING_REVISION = "007_learning_sessions"
PROGRESS_REVISION = "008_owned_progress"
LEARNING_TABLES = {"employee_learning_sessions", "review_attempts", "review_answers"}
PROGRESS_TABLES = {"owned_progress_check_ins", "progress_reviews"}


def migration_config(database_path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    return config


def current_heads(database_path: Path) -> tuple[str, ...]:
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.connect() as connection:
            return tuple(MigrationContext.configure(connection).get_current_heads())
    finally:
        engine.dispose()


def table_names(database_path: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_story_revisions_are_siblings_with_one_deterministic_merge_head(tmp_path: Path) -> None:
    config = migration_config(tmp_path / "graph.db")
    scripts = ScriptDirectory.from_config(config)

    learning = scripts.get_revision(LEARNING_REVISION)
    progress = scripts.get_revision(PROGRESS_REVISION)
    merge = scripts.get_revision(MERGE_REVISION)

    assert learning is not None and learning.down_revision == "006_owned_roadmaps"
    assert progress is not None and progress.down_revision == "006_owned_roadmaps"
    assert merge is not None
    assert merge.down_revision == (LEARNING_REVISION, PROGRESS_REVISION)
    assert scripts.get_heads() == [MERGE_REVISION]


@pytest.mark.parametrize("starting_head", [LEARNING_REVISION, PROGRESS_REVISION])
def test_combined_upgrade_converges_from_each_story_head(
    tmp_path: Path, starting_head: str,
) -> None:
    database_path = tmp_path / f"{starting_head}.db"
    config = migration_config(database_path)

    command.upgrade(config, starting_head)
    assert current_heads(database_path) == (starting_head,)

    command.upgrade(config, MERGE_REVISION)

    assert current_heads(database_path) == (MERGE_REVISION,)
    assert LEARNING_TABLES | PROGRESS_TABLES <= table_names(database_path)


def test_combined_release_from_foundation_applies_both_branches_and_one_head(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "combined.db"
    config = migration_config(database_path)

    command.upgrade(config, MERGE_REVISION)

    assert current_heads(database_path) == (MERGE_REVISION,)
    assert LEARNING_TABLES | PROGRESS_TABLES <= table_names(database_path)
