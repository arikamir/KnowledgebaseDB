"""Exact machine application-role policy."""

from __future__ import annotations

from auth.bearer import BearerValidationError, ValidatedPrincipal


OPERATION_ROLES = {
    "createRoadmap": "CareerAgent.Roadmap.Generate",
    "createGuidance": "CareerAgent.Guidance.Read",
    "createProgressCheckIn": "CareerAgent.Progress.Write",
    "getCoreCapabilities": "CareerAgent.Health.Read",
}


def require_machine_role(principal: ValidatedPrincipal, operation_id: str, allowed_roles: frozenset[str]) -> str:
    if principal.token_type != "application":
        raise BearerValidationError("WRONG_TOKEN_TYPE")
    required = OPERATION_ROLES.get(operation_id)
    if required is None or required not in principal.roles or not principal.roles.issubset(allowed_roles):
        raise BearerValidationError("MACHINE_ROLE_REQUIRED", 403)
    return required


def require_machine_owner(principal: ValidatedPrincipal, owner_client_id: str) -> None:
    if principal.client_id != owner_client_id:
        raise BearerValidationError("MACHINE_OWNER_MISMATCH", 403)
