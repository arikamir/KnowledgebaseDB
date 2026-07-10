"""Skill guidance API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent.contracts.skill_guidance import SkillGuidanceResponse, TopicGuidanceRequest
from agent.skill_guidance_service import SkillGuidanceService
from api.route_helpers import get_skill_guidance_service


router = APIRouter()


@router.post("/guidance", response_model=SkillGuidanceResponse)
def get_guidance(
    request: TopicGuidanceRequest,
    skill_service: SkillGuidanceService = Depends(get_skill_guidance_service),
) -> SkillGuidanceResponse:
    return skill_service.generate_guidance(request)

