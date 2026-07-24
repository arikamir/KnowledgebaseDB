"""API helpers that enforce validation-before-idempotency ordering."""

from __future__ import annotations

from typing import Any, Callable

from api.errors import ApiProblem
from storage.idempotency_repository import (
    IdempotencyConflict,
    IdempotencyDecision,
    IdempotencyRepository,
    canonical_request_hash,
)


def claim_idempotency(
    repository: IdempotencyRepository,
    *, actor_type: str, actor_id: str, operation: str, key: str, payload: Any,
    validate: Callable[[Any], None] | None = None,
) -> IdempotencyDecision:
    if not 16 <= len(key) <= 128:
        raise ApiProblem(422, "IDEMPOTENCY_KEY_INVALID", "Invalid idempotency key")
    if validate:
        validate(payload)
    try:
        return repository.claim(actor_type, actor_id, operation, key, canonical_request_hash(payload))
    except IdempotencyConflict as error:
        raise ApiProblem(409, error.code, "Idempotency conflict", retry_after=error.retry_after) from error
