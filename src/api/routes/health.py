"""Process-local liveness and dependency-aware readiness."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import os
from cryptography import x509
from cryptography.hazmat.primitives import serialization

router = APIRouter()


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request):
    checks: dict[str, Callable[[], bool]] = dict(getattr(request.app.state, "readiness_checks", {}))
    checks.setdefault("postgresql", lambda: _database_canary(request.app.state.container.database))
    certificate_path = os.getenv("CORE_TLS_PEM_PATH")
    expected_version = os.getenv("CORE_TLS_CERTIFICATE_VERSION")
    expected_sans = frozenset(filter(None, os.getenv("CORE_TLS_EXPECTED_SANS", "").split(",")))
    expected_issuer = os.getenv("CORE_TLS_EXPECTED_ISSUER", "")
    if certificate_path or expected_version:
        checks["key-material"] = MountedPemMaterialProbe(
            material_path=Path(certificate_path or ""),
            expected_version=expected_version or "",
            expected_sans=expected_sans,
            expected_issuer=expected_issuer,
        )
        checks.setdefault("tls-functional", lambda: request.url.scheme == "https")
    required = tuple(filter(None, (value.strip() for value in os.getenv("READINESS_REQUIRED_DEPENDENCIES", "").split(","))))
    failures = [name for name in required if name not in checks]
    failures.extend(name for name, check in checks.items() if not _safe_check(check))
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


@dataclass(frozen=True, slots=True)
class MountedPemMaterialProbe:
    material_path: Path
    expected_version: str
    expected_sans: frozenset[str]
    expected_issuer: str = ""

    def __call__(self) -> bool:
        if not self.expected_version:
            return False
        pem = self.material_path.read_bytes()
        certificate_start = pem.find(b"-----BEGIN CERTIFICATE-----")
        certificate_end = pem.find(b"-----END CERTIFICATE-----")
        private_key_start = pem.find(b"-----BEGIN PRIVATE KEY-----")
        private_key_end = pem.find(b"-----END PRIVATE KEY-----")
        if min(certificate_start, certificate_end, private_key_start, private_key_end) < 0:
            return False
        certificate_pem = pem[certificate_start:certificate_end + len(b"-----END CERTIFICATE-----")]
        private_key_pem = pem[private_key_start:private_key_end + len(b"-----END PRIVATE KEY-----")]
        certificate = x509.load_pem_x509_certificate(certificate_pem)
        private_key = serialization.load_pem_private_key(private_key_pem, password=None)
        if certificate.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ) != private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ):
            return False
        now = datetime.now(timezone.utc)
        if certificate.not_valid_after_utc <= now or certificate.not_valid_before_utc > now:
            return False
        extension = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        sans = frozenset(extension.value.get_values_for_type(x509.DNSName))
        issuer = certificate.issuer.rfc4514_string()
        return self.expected_sans.issubset(sans) and (
            not self.expected_issuer or self.expected_issuer in issuer
        )
