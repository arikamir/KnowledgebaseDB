"""Authenticated private-BFF session-revocation client."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import httpx

from storage.identity_models import SessionRevocationOutboxRecord


class RevocationDeliveryError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(slots=True)
class BffRevocationClient:
    base_url: str
    acquire_token: Callable[[], str]
    transport: httpx.BaseTransport | None = None
    timeout_seconds: float = 10.0

    def revoke(self, row: SessionRevocationOutboxRecord) -> None:
        token = self.acquire_token()
        if not token:
            raise RevocationDeliveryError("REVOCATION_TOKEN_UNAVAILABLE")
        payload = {
            "tenantId": row.tenant_id,
            "objectId": row.object_id,
            "reconciliationRunId": row.reconciliation_run_id,
            "departedAt": row.departed_at.isoformat(),
        }
        try:
            with httpx.Client(transport=self.transport, timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url.rstrip('/')}/internal/v1/session-revocations",
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )
        except httpx.HTTPError as error:
            raise RevocationDeliveryError("BFF_REVOCATION_UNAVAILABLE") from error
        if response.status_code != 200:
            code = "BFF_REVOCATION_FORBIDDEN" if response.status_code in {401, 403} else "BFF_REVOCATION_UNAVAILABLE"
            raise RevocationDeliveryError(code)
        body = response.json()
        if body.get("status") != "acknowledged" or body.get("reconciliationRunId") != row.reconciliation_run_id:
            raise RevocationDeliveryError("BFF_REVOCATION_ACK_INVALID")
