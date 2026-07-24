"""Shared FastAPI dependency helpers."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from agent.progress_service import ProgressService
from agent.roadmap_service import RoadmapService
from agent.settings import AppSettings, load_settings
from agent.skill_guidance_service import SkillGuidanceService
from skills.catalog import SkillCatalog, load_default_catalog
from storage.database import DatabaseManager
from storage.progress_repository import ProgressRepository
from storage.roadmap_repository import RoadmapRepository
from storage.identity_repository import IdentityRepository
from storage.idempotency_repository import IdempotencyRepository
from storage.learning_repository import LearningRepository
from agent.learning_service import LearningService
from agent.review_service import ReviewService


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    database: DatabaseManager
    catalog: SkillCatalog
    roadmap_repository: RoadmapRepository
    progress_repository: ProgressRepository
    roadmap_service: RoadmapService
    skill_guidance_service: SkillGuidanceService
    progress_service: ProgressService
    identity_repository: IdentityRepository
    idempotency_repository: IdempotencyRepository
    learning_repository: LearningRepository
    learning_service: LearningService
    review_service: ReviewService


def build_container(settings: AppSettings | None = None) -> AppContainer:
    resolved_settings = settings or load_settings()
    database = DatabaseManager.create(resolved_settings.database_url)
    catalog = load_default_catalog(resolved_settings)
    roadmap_repository = RoadmapRepository(database)
    progress_repository = ProgressRepository(database)
    roadmap_service = RoadmapService(
        repository=roadmap_repository,
        catalog=catalog,
        settings=resolved_settings,
    )
    skill_guidance_service = SkillGuidanceService(catalog=catalog)
    progress_service = ProgressService(
        roadmap_repository=roadmap_repository,
        progress_repository=progress_repository,
        roadmap_service=roadmap_service,
    )
    identity_repository = IdentityRepository(database)
    idempotency_repository = IdempotencyRepository(database)
    learning_repository = LearningRepository(database)
    learning_service = LearningService(learning_repository)
    review_service = ReviewService(learning_repository)
    return AppContainer(
        settings=resolved_settings,
        database=database,
        catalog=catalog,
        roadmap_repository=roadmap_repository,
        progress_repository=progress_repository,
        roadmap_service=roadmap_service,
        skill_guidance_service=skill_guidance_service,
        progress_service=progress_service,
        identity_repository=identity_repository,
        idempotency_repository=idempotency_repository,
        learning_repository=learning_repository,
        learning_service=learning_service,
        review_service=review_service,
    )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_roadmap_service(request: Request) -> RoadmapService:
    return get_container(request).roadmap_service


def get_skill_guidance_service(request: Request) -> SkillGuidanceService:
    return get_container(request).skill_guidance_service


def get_progress_service(request: Request) -> ProgressService:
    return get_container(request).progress_service


def get_learning_service(request: Request) -> LearningService:
    return get_container(request).learning_service


def get_review_service(request: Request) -> ReviewService:
    return get_container(request).review_service
