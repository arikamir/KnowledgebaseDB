"""Skill guidance API routes."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, Header, Request

from agent.contracts.skill_guidance import SkillGuidanceResponse, TopicGuidanceRequest
from agent.skill_guidance_service import SkillGuidanceService
from api.route_helpers import get_skill_guidance_service
from api.routes.authz import employee_or_machine_principal
from api.routes.registry import register_router
from auth.bearer import ValidatedPrincipal
from api.errors import ApiProblem
from api.idempotency import claim_idempotency
from storage.idempotency_repository import IdempotencyRepository


router = APIRouter()
foundation = APIRouter()
logger = logging.getLogger(__name__)


def guidance_principal(request: Request) -> ValidatedPrincipal:
    return employee_or_machine_principal(request, "createGuidance")


@router.post("/guidance", response_model=SkillGuidanceResponse)
def get_guidance(
    request: TopicGuidanceRequest,
    skill_service: SkillGuidanceService = Depends(get_skill_guidance_service),
) -> SkillGuidanceResponse:
    return skill_service.generate_guidance(request)


@foundation.post("/guidance", response_model=SkillGuidanceResponse, operation_id="createGuidance")
def create_guidance(
    request: TopicGuidanceRequest,
    http_request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    guidance_catalog_version: str | None = Header(default=None, alias="X-Guidance-Catalog-Version"),
    principal: ValidatedPrincipal = Depends(guidance_principal),
    skill_service: SkillGuidanceService = Depends(get_skill_guidance_service),
) -> SkillGuidanceResponse:
    started = time.monotonic()
    if guidance_catalog_version and guidance_catalog_version != skill_service.catalog.catalog_version:
        raise ApiProblem(409, "CONTRACT_VERSION_UNSUPPORTED", "Guidance catalog version is unsupported", retryable=False)
    try:
        topic = skill_service.resolve_active_topic(request.topic)
    except ApiProblem as problem:
        logger.info(
            "guidance request rejected",
            extra={"operation": "createGuidance", "outcome": problem.code, "catalog_version": skill_service.catalog.catalog_version},
        )
        raise
    repository: IdempotencyRepository = http_request.app.state.container.idempotency_repository
    payload = request.model_dump(mode="json")
    for generated_field in ("id", "created_at", "updated_at"):
        payload["employee_profile"].pop(generated_field, None)
    decision = claim_idempotency(
        repository,
        actor_type=principal.token_type,
        actor_id=principal.actor_id,
        operation="createGuidance",
        key=idempotency_key,
        payload=payload,
    )
    if decision.action == "replay" and decision.body is not None:
        return SkillGuidanceResponse.model_validate(decision.body)
    result = skill_service.generate_active_guidance(request, topic)
    repository.succeed(decision.record_id, 200, result.model_dump(mode="json"))
    logger.info(
        "guidance request completed",
        extra={
            "operation": "createGuidance",
            "outcome": "success",
            "topic": skill_service.catalog.topic_id(topic),
            "catalog_version": skill_service.catalog.catalog_version,
            "duration_ms": round((time.monotonic() - started) * 1000),
        },
    )
    return result


register_router(foundation, {"createGuidance"})
