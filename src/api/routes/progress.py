"""Progress review API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent.contracts.progress import ProgressCheckInRequest, ProgressReviewResponse
from agent.progress_service import ProgressService
from api.route_helpers import get_progress_service


router = APIRouter()


@router.post("/check-ins", response_model=ProgressReviewResponse)
def submit_check_in(
    request: ProgressCheckInRequest,
    progress_service: ProgressService = Depends(get_progress_service),
) -> ProgressReviewResponse:
    return progress_service.record_progress(request)

