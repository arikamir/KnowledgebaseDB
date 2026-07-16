"""FastAPI dependencies for strict delegated and machine authorization."""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from auth.bearer import BearerValidationError, ValidatedPrincipal


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="TOKEN_REQUIRED")
    return authorization.removeprefix("Bearer ").strip()


def principal_from_state(request: Request) -> ValidatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(status_code=401, detail="TOKEN_REQUIRED")
    return principal


def employee_principal(request: Request) -> ValidatedPrincipal:
    principal = principal_from_state(request)
    if principal.token_type != "employee":
        raise HTTPException(status_code=401, detail="WRONG_TOKEN_TYPE")
    return principal


def machine_principal(request: Request) -> ValidatedPrincipal:
    principal = principal_from_state(request)
    if principal.token_type != "application":
        raise HTTPException(status_code=401, detail="WRONG_TOKEN_TYPE")
    return principal


def authorization_http_error(error: BearerValidationError) -> HTTPException:
    return HTTPException(status_code=error.status, detail=error.code)
