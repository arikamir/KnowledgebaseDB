"""API router assembly."""

from __future__ import annotations

from fastapi import APIRouter

from api.routes.progress import router as progress_router
from api.routes.roadmap import router as roadmap_router
from api.routes.skills import router as skills_router


api_router = APIRouter()
api_router.include_router(roadmap_router, prefix="/roadmaps", tags=["roadmaps"])
api_router.include_router(skills_router, prefix="/skills", tags=["skills"])
api_router.include_router(progress_router, prefix="/progress", tags=["progress"])

