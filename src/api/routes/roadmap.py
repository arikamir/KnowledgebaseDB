"""Roadmap intake API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent.contracts.roadmap import RoadmapIntakeRequest, RoadmapIntakeResponse
from agent.roadmap_service import RoadmapService
from api.route_helpers import get_roadmap_service


router = APIRouter()


@router.post("", response_model=RoadmapIntakeResponse)
def create_roadmap(
    request: RoadmapIntakeRequest,
    roadmap_service: RoadmapService = Depends(get_roadmap_service),
) -> RoadmapIntakeResponse:
    return roadmap_service.create_roadmap(request)

