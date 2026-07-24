"""Strict single-tenant delegated and application-token validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

import jwt
from jwt import PyJWTError


class BearerValidationError(RuntimeError):
    def __init__(self, code: str, status: int = 401) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True, slots=True)
class BearerPolicy:
    tenant_id: str
    issuer: str
    audience: str
    bff_client_id: str
    employee_scope: str
    algorithms: tuple[str, ...] = ("RS256",)
    clock_skew_seconds: int = 300


@dataclass(frozen=True, slots=True)
class ValidatedPrincipal:
    token_type: str
    tenant_id: str
    actor_id: str
    client_id: str
    scopes: frozenset[str]
    roles: frozenset[str]


@dataclass(slots=True)
class SigningKeyCache:
    keys: dict[str, Any]
    refreshed_at: datetime
    refresh: Callable[[], tuple[dict[str, Any], datetime]]

    def key(self, kid: str, now: datetime) -> Any:
        age = now - self.refreshed_at
        if kid in self.keys and age <= timedelta(hours=6):
            return self.keys[kid]
        try:
            keys, refreshed_at = self.refresh()
        except Exception as error:
            if kid in self.keys and age <= timedelta(hours=24):
                return self.keys[kid]
            raise BearerValidationError("AUTH_KEY_METADATA_UNAVAILABLE", 503) from error
        self.keys, self.refreshed_at = keys, refreshed_at
        if kid not in keys:
            raise BearerValidationError("TOKEN_INVALID", 401)
        return keys[kid]

    def ready(self, now: datetime) -> bool:
        return bool(self.keys) and now - self.refreshed_at <= timedelta(hours=24)


def validate_claims(claims: Mapping[str, Any], policy: BearerPolicy, *, delegated: bool, now: datetime | None = None) -> ValidatedPrincipal:
    now = now or datetime.now(timezone.utc)
    invalid = "DELEGATED_TOKEN_INVALID" if delegated else "MACHINE_TOKEN_INVALID"
    required = ("tid", "iss", "aud", "nbf", "exp")
    if any(claim not in claims for claim in required):
        raise BearerValidationError(invalid)
    if claims["tid"] != policy.tenant_id or claims["iss"] != policy.issuer or claims["aud"] != policy.audience:
        raise BearerValidationError(invalid)
    skew = min(policy.clock_skew_seconds, 300)
    if float(claims["nbf"]) > now.timestamp() + skew or float(claims["exp"]) <= now.timestamp() - skew:
        raise BearerValidationError(invalid)
    client_id = claims.get("azp") or claims.get("appid")
    if not isinstance(client_id, str) or not client_id:
        raise BearerValidationError(invalid)
    scopes = frozenset(str(claims.get("scp", "")).split())
    role_value = claims.get("roles", [])
    roles = frozenset(role_value if isinstance(role_value, list) else [])
    if delegated:
        if roles and not scopes:
            raise BearerValidationError("WRONG_TOKEN_TYPE")
        if client_id != policy.bff_client_id:
            raise BearerValidationError(invalid)
        if policy.employee_scope not in scopes:
            raise BearerValidationError("DELEGATED_SCOPE_REQUIRED", 403)
        actor_id = claims.get("oid")
        if not isinstance(actor_id, str) or not actor_id:
            raise BearerValidationError(invalid)
        return ValidatedPrincipal("employee", policy.tenant_id, actor_id, client_id, scopes, roles)
    if scopes:
        raise BearerValidationError("WRONG_TOKEN_TYPE")
    return ValidatedPrincipal("application", policy.tenant_id, client_id, client_id, scopes, roles)


def decode_and_validate(token: str, policy: BearerPolicy, cache: SigningKeyCache, *, delegated: bool, now: datetime | None = None) -> ValidatedPrincipal:
    now = now or datetime.now(timezone.utc)
    invalid = "DELEGATED_TOKEN_INVALID" if delegated else "MACHINE_TOKEN_INVALID"
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in policy.algorithms or not isinstance(header.get("kid"), str):
            raise BearerValidationError(invalid)
        key = cache.key(header["kid"], now)
        claims = jwt.decode(
            token,
            key,
            algorithms=list(policy.algorithms),
            audience=policy.audience,
            issuer=policy.issuer,
            leeway=min(policy.clock_skew_seconds, 300),
            options={"require": ["exp", "nbf", "iss", "aud", "tid"]},
        )
    except BearerValidationError as error:
        if error.code == "TOKEN_INVALID":
            raise BearerValidationError(invalid) from error
        raise
    except PyJWTError as error:
        raise BearerValidationError(invalid) from error
    return validate_claims(claims, policy, delegated=delegated, now=now)
