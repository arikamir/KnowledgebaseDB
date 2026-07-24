"""Self-registering owner-scoped learning and review routes."""

from __future__ import annotations

import logging
import time
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field

from agent.learning_service import LearningService
from agent.next_action import MilestoneCandidate, select_next_action
from agent.review_service import ReviewRateLimited, ReviewService
from api.errors import ApiProblem
from api.idempotency import claim_idempotency
from api.route_helpers import get_learning_service, get_review_service
from api.routes.authz import employee_principal
from api.routes.registry import register_router
from auth.bearer import ValidatedPrincipal


class ReviewAnswerBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_key: str = Field(min_length=1)


class LabReportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str
    comment: str | None = Field(default=None, max_length=1000)


router = APIRouter()
logger = logging.getLogger(__name__)


def _problem(error: ValueError) -> ApiProblem:
    code = str(error)
    status = 404 if code.endswith("NOT_FOUND") else 409 if any(value in code for value in ("FINALIZED", "COMPLETED", "RETIRED")) else 422
    return ApiProblem(status, code, "Learning operation rejected", retryable=False)


def _mutation(request: Request, principal: ValidatedPrincipal, operation: str, key: str, payload: dict, execute, success_status: int = 200):
    started = time.monotonic()
    repository = request.app.state.container.idempotency_repository
    decision = claim_idempotency(repository, actor_type="employee", actor_id=principal.actor_id, operation=operation, key=key, payload=payload)
    if decision.action == "replay" and decision.body is not None:
        return decision.body
    try:
        result = execute()
    except ReviewRateLimited as error:
        repository.fail(decision.record_id, retryable=True, status=429, body={"code": str(error)}, retry_after_seconds=error.retry_after_seconds)
        logger.info("learning mutation completed", extra={"operation": operation, "outcome": str(error), "duration_ms": round((time.monotonic() - started) * 1000)})
        raise ApiProblem(429, str(error), "Review retry rate limited", retry_after=error.retry_after_seconds, retryable=True) from error
    except ValueError as error:
        repository.fail(decision.record_id, retryable=False, status=_problem(error).status, body={"code": str(error)})
        logger.info("learning mutation completed", extra={"operation": operation, "outcome": str(error), "duration_ms": round((time.monotonic() - started) * 1000)})
        raise _problem(error) from error
    repository.succeed(decision.record_id, success_status, jsonable_encoder(result))
    logger.info("learning mutation completed", extra={"operation": operation, "outcome": "success", "duration_ms": round((time.monotonic() - started) * 1000)})
    return result


@router.get("/learning-sessions", operation_id="listLearningSessions")
def list_sessions(roadmap_id: str = Query(min_length=1), principal: ValidatedPrincipal = Depends(employee_principal), service: LearningService = Depends(get_learning_service)):
    return service.repository.list_sessions(principal.actor_id, roadmap_id)


@router.post("/learning-sessions/{session_id}/start", operation_id="startLearningSession")
def start_session(session_id: str, request: Request, idempotency_key: str = Header(alias="Idempotency-Key"), principal: ValidatedPrincipal = Depends(employee_principal), service: LearningService = Depends(get_learning_service)):
    version = service.repository.latest_content_version(session_id)
    if version is None:
        raise ApiProblem(404, "LEARNING_CONTENT_NOT_FOUND", "Learning content not found", retryable=False)
    return _mutation(request, principal, "startLearningSession", idempotency_key, {"content_id": session_id, "content_version": version}, lambda: service.start(principal.actor_id, session_id, version))


@router.get("/learning-sessions/{session_id}", operation_id="getLearningSession")
def get_session(session_id: str, principal: ValidatedPrincipal = Depends(employee_principal), service: LearningService = Depends(get_learning_service)):
    try: return service.get(principal.actor_id, session_id)
    except ValueError as error: raise _problem(error) from error


@router.put("/learning-sessions/{session_id}/steps/{step_id}/completion", operation_id="completeLearningStep")
def complete_step(session_id: str, step_id: str, request: Request, idempotency_key: str = Header(alias="Idempotency-Key"), principal: ValidatedPrincipal = Depends(employee_principal), service: LearningService = Depends(get_learning_service)):
    return _mutation(request, principal, "completeLearningStep", idempotency_key, {"session_id": session_id, "step_id": step_id}, lambda: service.complete_step(principal.actor_id, session_id, step_id))


@router.get("/learning-sessions/{session_id}/review-attempts", operation_id="listReviewAttempts")
def list_attempts(session_id: str, principal: ValidatedPrincipal = Depends(employee_principal), service: ReviewService = Depends(get_review_service)):
    return service.repository.list_attempts(principal.actor_id, session_id)


@router.post("/learning-sessions/{session_id}/review-attempts", operation_id="createReviewAttempt")
def create_attempt(session_id: str, request: Request, idempotency_key: str = Header(alias="Idempotency-Key"), principal: ValidatedPrincipal = Depends(employee_principal), service: ReviewService = Depends(get_review_service)):
    return _mutation(request, principal, "createReviewAttempt", idempotency_key, {"session_id": session_id}, lambda: service.start_attempt(principal.actor_id, session_id))


@router.get("/review-attempts/{attempt_id}", operation_id="getReviewAttempt")
def get_attempt(attempt_id: str, principal: ValidatedPrincipal = Depends(employee_principal), service: ReviewService = Depends(get_review_service)):
    result = service.repository.get_attempt(principal.actor_id, attempt_id)
    if result is None: raise ApiProblem(404, "REVIEW_ATTEMPT_NOT_FOUND", "Review attempt not found", retryable=False)
    return result


@router.put("/review-attempts/{attempt_id}/answers/{question_id}", operation_id="answerReviewQuestion")
def answer(attempt_id: str, question_id: str, body: ReviewAnswerBody, request: Request, idempotency_key: str = Header(alias="Idempotency-Key"), principal: ValidatedPrincipal = Depends(employee_principal), service: ReviewService = Depends(get_review_service)):
    return _mutation(request, principal, "answerReviewQuestion", idempotency_key, {"attempt_id": attempt_id, "question_id": question_id, **body.model_dump()}, lambda: service.answer(principal.actor_id, attempt_id, question_id, body.answer_key))


@router.post("/review-attempts/{attempt_id}/submit", operation_id="submitReviewAttempt")
def submit(attempt_id: str, request: Request, idempotency_key: str = Header(alias="Idempotency-Key"), principal: ValidatedPrincipal = Depends(employee_principal), service: ReviewService = Depends(get_review_service)):
    return _mutation(request, principal, "submitReviewAttempt", idempotency_key, {"attempt_id": attempt_id}, lambda: service.submit(principal.actor_id, attempt_id))


@router.post("/lab-references/{lab_reference_id}/reports", status_code=202, operation_id="reportLabReference")
def report_lab(lab_reference_id: str, body: LabReportBody, request: Request, idempotency_key: str = Header(alias="Idempotency-Key"), principal: ValidatedPrincipal = Depends(employee_principal), service: LearningService = Depends(get_learning_service)):
    try:
        session_id = service.repository.session_for_lab(principal.actor_id, lab_reference_id)
    except ValueError as error:
        raise _problem(error) from error
    return _mutation(request, principal, "reportLabReference", idempotency_key, {"session_id": session_id, "lab_reference_id": lab_reference_id, **body.model_dump()}, lambda: service.report_lab(principal.actor_id, session_id, lab_reference_id, body.reason, body.comment), 202)


@router.get("/learning/next-action", operation_id="getNextLearningAction")
def next_action(roadmap_id: str = Query(min_length=1), principal: ValidatedPrincipal = Depends(employee_principal), service: LearningService = Depends(get_learning_service)):
    learning = service.repository.learning_candidates(principal.actor_id, roadmap_id)
    roadmap = service.repository.database
    from storage.roadmap_models import RoadmapMilestoneRecord
    from sqlalchemy import select
    with roadmap.session() as session:
        records = session.execute(select(RoadmapMilestoneRecord).where(RoadmapMilestoneRecord.roadmap_id == roadmap_id)).scalars()
        milestones = [MilestoneCandidate(roadmap_id, item.milestone_key, item.ordinal, item.title, item.status == "completed") for item in records]
    selected = select_next_action(roadmap_id, milestones, learning)
    return {
        "kind": selected.action_type,
        "title": selected.title,
        "reason": "Selected from the highest-priority unresolved learning state.",
        "target": selected.milestone_key or selected.roadmap_id,
    }


register_router(router, {"listLearningSessions", "startLearningSession", "getLearningSession", "completeLearningStep", "listReviewAttempts", "createReviewAttempt", "getReviewAttempt", "answerReviewQuestion", "submitReviewAttempt", "reportLabReference", "getNextLearningAction"})
