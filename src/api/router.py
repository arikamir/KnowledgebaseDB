"""API router assembly."""

from __future__ import annotations

from fastapi import APIRouter

from api.routes.progress import router as progress_router
from api.routes.roadmap import router as roadmap_router
from api.routes.skills import router as skills_router
from api.routes.registry import foundation_router, register_router, registered_operation_ids
from api.routes.capabilities import router as capabilities_router
from api.routes.identity import router as identity_router
from api.routes import learning as _learning  # noqa: F401


api_router = APIRouter()
api_router.include_router(roadmap_router, prefix="/roadmaps", tags=["roadmaps"])
api_router.include_router(skills_router, prefix="/skills", tags=["skills"])
api_router.include_router(progress_router, prefix="/progress", tags=["progress"])

if "getCoreCapabilities" not in registered_operation_ids():
    register_router(capabilities_router, {"getCoreCapabilities"})
if "bootstrapEmployeeSession" not in registered_operation_ids():
    register_router(identity_router, {"bootstrapEmployeeSession"})
api_router.include_router(foundation_router)
