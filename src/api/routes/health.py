"""Process-local liveness and dependency-aware readiness."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter()


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request):
    checks: dict[str, Callable[[], bool]] = getattr(request.app.state, "readiness_checks", {})
    if not checks:
        database = request.app.state.container.database
        checks = {"postgresql": lambda: _database_canary(database)}
    failures = [name for name, check in checks.items() if not _safe_check(check)]
    if failures:
        return JSONResponse({"status": "unready", "failedDependencies": failures}, status_code=503)
    return {"status": "ready"}


def _database_canary(database) -> bool:
    with database.session() as session:
        session.execute(text("SELECT 1"))
    return True


def _safe_check(check: Callable[[], bool]) -> bool:
    try:
        return bool(check())
    except Exception:
        return False
