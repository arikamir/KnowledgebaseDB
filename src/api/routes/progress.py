"""Authenticated owner-scoped progress review API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from agent.contracts.progress import ProgressCheckInRequest, ProgressReviewResponse
from agent.progress_service import ProgressService
from api.errors import ApiProblem
from api.idempotency import claim_idempotency
from api.route_helpers import get_progress_service
from api.routes.authz import authorization_http_error, employee_principal, principal_from_state
from api.routes.registry import register_router
from auth.bearer import BearerValidationError, ValidatedPrincipal
from auth.machine_roles import require_machine_role
from storage.progress_repository import ProgressRoadmapNotFound, RoadmapVersionConflict


router = APIRouter()
foundation = APIRouter()


@router.post("/check-ins", response_model=ProgressReviewResponse)
def submit_check_in(
    request: ProgressCheckInRequest,
    progress_service: ProgressService = Depends(get_progress_service),
) -> ProgressReviewResponse:
    return progress_service.record_progress(request)


def progress_writer_principal(request: Request) -> ValidatedPrincipal:
    """Accept a validated delegated employee or approved progress application."""
    existing = getattr(request.state, "principal", None)
    if existing is not None:
        principal = existing
    else:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer ") or not authorization.removeprefix("Bearer ").strip():
            raise ApiProblem(401, "TOKEN_REQUIRED", "Authentication required", retryable=False)
        token = authorization.removeprefix("Bearer ").strip()
        principal = None
        last_error: BearerValidationError | None = None
        for attribute, expected_type in (
            ("validate_delegated_token", "employee"),
            ("validate_machine_token", "application"),
        ):
            validator = getattr(request.app.state, attribute, None)
            if validator is None:
                continue
            try:
                candidate = validator(token)
            except BearerValidationError as error:
                last_error = error
                continue
            if candidate.token_type == expected_type:
                principal = candidate
                break
        if principal is None:
            if last_error is not None:
                raise authorization_http_error(last_error)
            principal = principal_from_state(request)
        request.state.principal = principal

    if principal.token_type == "application":
        try:
            require_machine_role(
                principal,
                "createProgressCheckIn",
                frozenset({"CareerAgent.Progress.Write"}),
            )
        except BearerValidationError as error:
            raise authorization_http_error(error) from error
    elif principal.token_type != "employee":
        raise ApiProblem(401, "WRONG_TOKEN_TYPE", "Wrong token type", retryable=False)
    return principal


def _replay_or_none(decision) -> ProgressReviewResponse | None:
    if decision.action != "replay" or decision.body is None:
        return None
    if decision.status is not None and decision.status >= 400:
        raise ApiProblem(
            decision.status,
            str(decision.body.get("code", "PROGRESS_REJECTED")),
            str(decision.body.get("title", "Progress operation rejected")),
            detail=(str(decision.body["detail"]) if decision.body.get("detail") else None),
            retryable=bool(decision.body.get("retryable", False)),
        )
    return ProgressReviewResponse.model_validate(decision.body)


@foundation.post(
    "/progress/check-ins",
    response_model=ProgressReviewResponse,
    operation_id="createProgressCheckIn",
)
def create_owned_progress_check_in(
    progress_request: ProgressCheckInRequest,
    http_request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: ValidatedPrincipal = Depends(progress_writer_principal),
    progress_service: ProgressService = Depends(get_progress_service),
) -> ProgressReviewResponse:
    repository = http_request.app.state.container.idempotency_repository
    decision = claim_idempotency(
        repository,
        actor_type=principal.token_type,
        actor_id=principal.actor_id,
        operation="createProgressCheckIn",
        key=idempotency_key,
        payload=progress_request.model_dump(mode="json"),
    )
    replay = _replay_or_none(decision)
    if replay is not None:
        return replay
    try:
        result = progress_service.record_owned_progress(
            progress_request,
            actor_type=principal.token_type,
            actor_id=principal.actor_id,
            idempotency_record_id=decision.record_id,
        )
    except ProgressRoadmapNotFound as error:
        body = {"status": 404, "code": "ROADMAP_NOT_FOUND", "title": "Roadmap not found", "retryable": False}
        repository.fail(decision.record_id, retryable=False, status=404, body=body)
        raise ApiProblem(404, "ROADMAP_NOT_FOUND", "Roadmap not found", retryable=False) from error
    except RoadmapVersionConflict as error:
        body = {
            "status": 409,
            "code": "ROADMAP_VERSION_CONFLICT",
            "title": "Roadmap changed during progress review",
            "detail": "Reload the authoritative roadmap and submit the preserved notes with a new intended-action key.",
            "retryable": False,
        }
        repository.fail(decision.record_id, retryable=False, status=409, body=body)
        raise ApiProblem(
            409,
            "ROADMAP_VERSION_CONFLICT",
            "Roadmap changed during progress review",
            detail=body["detail"],
            retryable=False,
        ) from error
    except ValueError as error:
        code = str(error).split(":", 1)[0]
        status = 409 if code == "LEGACY_RECORD_NOT_UI_COMPATIBLE" else 422
        body = {"status": status, "code": code, "title": "Progress check-in rejected", "retryable": False}
        repository.fail(decision.record_id, retryable=False, status=status, body=body)
        raise ApiProblem(status, code, "Progress check-in rejected", retryable=False) from error
    repository.succeed(
        decision.record_id,
        200,
        result.model_dump(mode="json"),
        result.check_in.id if result.check_in else None,
    )
    return result


@foundation.get(
    "/progress/reviews",
    response_model=ProgressReviewResponse,
    operation_id="getProgressReview",
)
def get_owned_progress_review(
    roadmap_id: str,
    principal: ValidatedPrincipal = Depends(employee_principal),
    progress_service: ProgressService = Depends(get_progress_service),
) -> ProgressReviewResponse:
    result = progress_service.restore_owned_review(
        roadmap_id,
        employee_identity_id=principal.actor_id,
    )
    if result is None:
        raise ApiProblem(404, "PROGRESS_REVIEW_NOT_FOUND", "Progress review not found", retryable=False)
    return result


register_router(foundation, {"createProgressCheckIn", "getProgressReview"})
