"""Roadmap intake API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from agent.contracts.roadmap import RoadmapIntakeRequest, RoadmapIntakeResponse
from agent.roadmap_service import RoadmapService
from api.route_helpers import get_roadmap_service
from api.routes.authz import employee_principal
from api.routes.registry import register_router
from auth.bearer import ValidatedPrincipal
from api.idempotency import claim_idempotency
from storage.idempotency_repository import IdempotencyRepository
import logging
import time


router = APIRouter()
foundation = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=RoadmapIntakeResponse)
def create_roadmap(
    request: RoadmapIntakeRequest,
    roadmap_service: RoadmapService = Depends(get_roadmap_service),
) -> RoadmapIntakeResponse:
    return roadmap_service.create_roadmap(request)


@foundation.post("/roadmaps", response_model=RoadmapIntakeResponse, operation_id="createRoadmap")
def create_owned_roadmap(request: RoadmapIntakeRequest, http_request: Request, idempotency_key: str = Header(alias="Idempotency-Key"), principal: ValidatedPrincipal = Depends(employee_principal), roadmap_service: RoadmapService = Depends(get_roadmap_service)) -> RoadmapIntakeResponse:
    started = time.monotonic()
    repository: IdempotencyRepository = http_request.app.state.container.idempotency_repository
    decision = claim_idempotency(repository, actor_type="employee", actor_id=principal.actor_id, operation="createRoadmap", key=idempotency_key, payload=request.model_dump(mode="json"))
    if decision.action == "replay" and decision.body is not None:
        return RoadmapIntakeResponse.model_validate(decision.body)
    result = roadmap_service.create_owned_roadmap(request, employee_identity_id=principal.actor_id)
    repository.succeed(decision.record_id, 200, result.model_dump(mode="json"), result.roadmap_id)
    logger.info("roadmap request completed", extra={"operation": "createRoadmap", "outcome": result.status, "duration_ms": round((time.monotonic() - started) * 1000)})
    return result


@foundation.get("/roadmaps", operation_id="listRoadmaps")
def list_owned_roadmaps(principal: ValidatedPrincipal = Depends(employee_principal), roadmap_service: RoadmapService = Depends(get_roadmap_service)):
    return roadmap_service.repository.list_employee_owned(principal.actor_id)


@foundation.get("/roadmaps/{roadmap_id}", operation_id="getRoadmap")
def get_owned_roadmap(roadmap_id: str, principal: ValidatedPrincipal = Depends(employee_principal), roadmap_service: RoadmapService = Depends(get_roadmap_service)):
    try:
        roadmap = roadmap_service.repository.get_employee_owned(roadmap_id, principal.actor_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if roadmap is None:
        raise HTTPException(status_code=404, detail="ROADMAP_NOT_FOUND")
    return roadmap


register_router(foundation, {"createRoadmap", "listRoadmaps", "getRoadmap"})
