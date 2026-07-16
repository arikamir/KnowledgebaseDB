from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from agent.contracts.roadmap import RoadmapIntakeRequest
from knowledge.schemas import EmployeeProfile
from storage.database import Base, DatabaseManager
from storage.identity_models import EmployeeIdentityRecord
from storage.progress_models import ProgressCheckInRecord, ProgressReviewRecord


ROOT = Path(__file__).resolve().parents[2]


def test_progress_revision_is_a_sibling_head_with_owner_registration() -> None:
    source = (ROOT / "alembic/versions/008_owned_progress.py").read_text()

    assert 'down_revision = "006_owned_roadmaps"' in source
    assert 'branch_labels = ("progress",)' in source
    assert "owned_progress_check_ins" in source
    assert "progress_reviews" in source
    assert source.count("retention_relationship_registry") >= 2


def test_progress_metadata_enforces_owned_roadmap_graph() -> None:
    check_in_constraints = {
        constraint.name for constraint in ProgressCheckInRecord.__table__.constraints
    }
    review_constraints = {
        constraint.name for constraint in ProgressReviewRecord.__table__.constraints
    }
    check_in_indexes = {index.name for index in ProgressCheckInRecord.__table__.indexes}
    review_indexes = {index.name for index in ProgressReviewRecord.__table__.indexes}

    assert "ck_progress_check_in_exact_owner" in check_in_constraints
    assert "fk_progress_check_in_employee_roadmap" in check_in_constraints
    assert "fk_progress_check_in_application_roadmap" in check_in_constraints
    assert "ck_progress_review_exact_owner" in review_constraints
    assert "fk_progress_review_employee_check_in" in review_constraints
    assert "fk_progress_review_application_check_in" in review_constraints
    assert "ix_progress_check_in_employee_latest" in check_in_indexes
    assert "ix_progress_check_in_application_latest" in check_in_indexes
    assert "ix_progress_review_employee_latest" in review_indexes
    assert "ix_progress_review_application_latest" in review_indexes


def test_progress_tables_are_registered_for_local_bootstrap(tmp_path: Path) -> None:
    database = DatabaseManager.create(f"sqlite:///{tmp_path / 'progress.db'}")

    tables = set(inspect(database.engine).get_table_names())

    assert {"owned_progress_check_ins", "progress_reviews"} <= tables
    assert ProgressCheckInRecord.__table__ is Base.metadata.tables["owned_progress_check_ins"]
    assert ProgressReviewRecord.__table__ is Base.metadata.tables["progress_reviews"]


def test_owned_progress_persistence_restores_latest_review(app_container) -> None:
    owner_id = "employee-progress-owner"
    profile = EmployeeProfile(
        role="Linux administrator",
        experience_level="intermediate",
        target_role="DevOps engineer",
        available_time_per_week=6,
        target_specializations=["Terraform"],
    )
    with app_container.database.session() as session:
        session.add(EmployeeIdentityRecord(
            id=owner_id,
            tenant_id="tenant-progress",
            object_id="object-progress",
            display_name="Progress Owner",
            employee_profile_id=profile.id,
        ))
    result = app_container.roadmap_service.create_roadmap(
        RoadmapIntakeRequest(employee_profile=profile)
    )
    assert result.roadmap is not None
    roadmap = result.roadmap
    app_container.roadmap_repository.save_owned_roadmap(
        roadmap, employee_identity_id=owner_id
    )
    decision = app_container.idempotency_repository.claim(
        "employee", owner_id, "createProgressCheckIn", "progress-key", "request-hash"
    )
    milestone = roadmap.milestones[0]
    milestone_snapshot = [item.model_dump(mode="json") for item in roadmap.milestones]

    app_container.progress_repository.save_owned_review(
        check_in_id="check-in-1",
        review_id="review-1",
        actor_type="employee",
        employee_identity_id=owner_id,
        roadmap_id=roadmap.id,
        idempotency_record_id=decision.record_id,
        notes="Keep this note",
        completed_step_references=[milestone.title],
        normalized_milestone_keys=["milestone-key-1"],
        new_goals=["GitOps"],
        prior_roadmap_snapshot=roadmap.model_dump(mode="json"),
        updated_roadmap_snapshot=roadmap.model_dump(mode="json"),
        current_status="in_progress",
        gaps=["GitOps"],
        milestone_snapshot=milestone_snapshot,
        next_action={
            "kind": "continue_milestone",
            "title": milestone.title,
            "target": "milestone-key-1",
            "reason": "Continue the next incomplete milestone.",
        },
        presentation="Progress recorded.",
        follow_up_prompt="Continue learning.",
    )

    restored = app_container.progress_repository.get_latest_owned_review(
        roadmap.id, employee_identity_id=owner_id
    )

    assert restored is not None
    assert restored["check_in"]["notes"] == "Keep this note"
    assert restored["check_in"]["completed_steps"] == [milestone.title]
    assert restored["check_in"]["normalized_milestone_keys"] == ["milestone-key-1"]
    assert restored["next_action"]["kind"] == "continue_milestone"
    assert app_container.progress_repository.get_latest_owned_review(
        roadmap.id, employee_identity_id="foreign-owner"
    ) is None
