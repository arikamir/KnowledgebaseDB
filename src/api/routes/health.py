"""Process-local liveness and dependency-aware readiness."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.primitives import serialization

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


@dataclass(frozen=True, slots=True)
class MountedKeyMaterialProbe:
    certificate_path: Path
    private_key_path: Path
    version_path: Path
    expected_version: str
    expected_sans: frozenset[str]

    def __call__(self) -> bool:
        if self.version_path.read_text(encoding="utf-8").strip() != self.expected_version:
            return False
        certificate = x509.load_pem_x509_certificate(self.certificate_path.read_bytes())
        serialization.load_pem_private_key(self.private_key_path.read_bytes(), password=None)
        now = datetime.now(timezone.utc)
        if certificate.not_valid_after_utc <= now or certificate.not_valid_before_utc > now:
            return False
        extension = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        sans = frozenset(extension.value.get_values_for_type(x509.DNSName))
        return self.expected_sans.issubset(sans)
