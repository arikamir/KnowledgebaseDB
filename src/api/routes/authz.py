"""FastAPI dependencies for strict delegated and machine authorization."""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from auth.bearer import BearerValidationError, ValidatedPrincipal
from auth.machine_roles import OPERATION_ROLES, require_machine_role


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="TOKEN_REQUIRED")
    return authorization.removeprefix("Bearer ").strip()


def principal_from_state(request: Request) -> ValidatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(status_code=401, detail="TOKEN_REQUIRED")
    return principal


def _authorization_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="TOKEN_REQUIRED")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="TOKEN_REQUIRED")
    return token


def employee_principal(request: Request) -> ValidatedPrincipal:
    validator = getattr(request.app.state, "validate_delegated_token", None)
    if validator is not None:
        try:
            principal = validator(_authorization_token(request))
        except BearerValidationError as error:
            raise authorization_http_error(error) from error
        request.state.principal = principal
    else:
        principal = principal_from_state(request)
    if principal.token_type != "employee":
        raise HTTPException(status_code=401, detail="WRONG_TOKEN_TYPE")
    return principal


def machine_principal(request: Request) -> ValidatedPrincipal:
    validator = getattr(request.app.state, "validate_machine_token", None)
    if validator is not None:
        try:
            principal = validator(_authorization_token(request))
        except BearerValidationError as error:
            raise authorization_http_error(error) from error
        request.state.principal = principal
    else:
        principal = principal_from_state(request)
    if principal.token_type != "application":
        raise HTTPException(status_code=401, detail="WRONG_TOKEN_TYPE")
    return principal


def employee_or_machine_principal(request: Request, operation_id: str) -> ValidatedPrincipal:
    """Validate one bearer without allowing token-type impersonation."""
    existing = getattr(request.state, "principal", None)
    if existing is not None:
        principal = existing
    else:
        token = _authorization_token(request)
        principal = None
        last_error: BearerValidationError | None = None
        for attribute, expected in (("validate_delegated_token", "employee"), ("validate_machine_token", "application")):
            validator = getattr(request.app.state, attribute, None)
            if validator is None:
                continue
            try:
                candidate = validator(token)
            except BearerValidationError as error:
                last_error = error
                continue
            if candidate.token_type == expected:
                principal = candidate
                break
        if principal is None:
            if last_error is not None:
                raise authorization_http_error(last_error)
            principal = principal_from_state(request)
        request.state.principal = principal
    if principal.token_type == "application":
        required = OPERATION_ROLES[operation_id]
        try:
            require_machine_role(principal, operation_id, frozenset({required}))
        except BearerValidationError as error:
            raise authorization_http_error(error) from error
    elif principal.token_type != "employee":
        raise HTTPException(status_code=401, detail="WRONG_TOKEN_TYPE")
    return principal


def authorization_http_error(error: BearerValidationError) -> HTTPException:
    return HTTPException(status_code=error.status, detail=error.code)
