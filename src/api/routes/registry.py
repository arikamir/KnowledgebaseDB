"""Foundation-owned core route registry."""

from __future__ import annotations

from fastapi import APIRouter

from api.generated.validation import validate_registered_operations

foundation_router = APIRouter(prefix="/api/v1")
_operation_ids: set[str] = set()


def register_router(router: APIRouter, operation_ids: set[str]) -> None:
    if _operation_ids.intersection(operation_ids):
        raise RuntimeError("duplicate operation registration")
    validate_registered_operations(operation_ids)
    _operation_ids.update(operation_ids)
    foundation_router.include_router(router)


def registered_operation_ids() -> frozenset[str]:
    return frozenset(_operation_ids)
