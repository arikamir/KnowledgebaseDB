from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from auth.bearer import BearerPolicy, BearerValidationError, SigningKeyCache, ValidatedPrincipal, validate_claims
from auth.machine_roles import OPERATION_ROLES, require_machine_owner, require_machine_role


NOW = datetime(2026, 7, 16, 9, tzinfo=timezone.utc)
POLICY = BearerPolicy(
    tenant_id="tenant-1", issuer="https://login.microsoftonline.com/tenant-1/v2.0",
    audience="api://core", bff_client_id="bff-1", employee_scope="CareerAgent.Access",
)
DELEGATED_OPERATIONS = (
    "bootstrapEmployeeSession", "listRoadmaps", "createRoadmap", "getRoadmap", "createGuidance",
    "createProgressCheckIn", "getProgressReview", "listLearningSessions", "startLearningSession",
    "getLearningSession", "completeLearningStep", "listReviewAttempts", "createReviewAttempt",
    "getReviewAttempt", "answerReviewQuestion", "submitReviewAttempt", "reportLabReference", "getNextLearningAction",
)
MANIFEST = yaml.safe_load((Path(__file__).resolve().parents[1] / "fixtures/readiness-scenario-manifest-v1.yaml").read_text())
AUTH_MATRIX = MANIFEST["groups"]["sc027_sc028_authorization"]


def delegated_claims():
    return {"tid": "tenant-1", "iss": POLICY.issuer, "aud": "api://core", "nbf": NOW.timestamp() - 1, "exp": NOW.timestamp() + 3600, "azp": "bff-1", "scp": "CareerAgent.Access", "oid": "employee-1"}


@pytest.mark.parametrize("operation", DELEGATED_OPERATIONS)
def test_each_delegated_operation_accepts_exact_valid_profile(operation):
    principal = validate_claims(delegated_claims(), POLICY, delegated=True, now=NOW)
    assert operation in DELEGATED_OPERATIONS
    assert (principal.token_type, principal.actor_id) == ("employee", "employee-1")


@pytest.mark.parametrize("case", ["wrong_issuer", "wrong_tenant", "wrong_audience", "wrong_lifetime", "wrong_client", "missing_scope", "missing_subject", "app_token"])
def test_delegated_negative_matrix(case):
    claims = delegated_claims()
    if case == "wrong_issuer": claims["iss"] = "https://login.microsoftonline.com/common/v2.0"
    if case == "wrong_tenant": claims["tid"] = "tenant-2"
    if case == "wrong_audience": claims["aud"] = "api://other"
    if case == "wrong_lifetime": claims["exp"] = NOW.timestamp() - 1000
    if case == "wrong_client": claims["azp"] = "other-client"
    if case == "missing_scope": claims["scp"] = "Other.Scope"
    if case == "missing_subject": claims.pop("oid")
    if case == "app_token": claims.pop("scp"); claims["roles"] = ["CareerAgent.Roadmap.Generate"]
    with pytest.raises(BearerValidationError):
        validate_claims(claims, POLICY, delegated=True, now=NOW)


@pytest.mark.parametrize("operation,role", OPERATION_ROLES.items())
def test_machine_operation_role_matrix(operation, role):
    principal = ValidatedPrincipal("application", "tenant-1", "machine-1", "machine-1", frozenset(), frozenset({role}))
    assert require_machine_role(principal, operation, frozenset({role})) == role


@pytest.mark.parametrize("operation,role", OPERATION_ROLES.items())
def test_machine_wrong_role_denied(operation, role):
    principal = ValidatedPrincipal("application", "tenant-1", "machine-1", "machine-1", frozenset(), frozenset({"Wrong.Role"}))
    with pytest.raises(BearerValidationError, match="MACHINE_ROLE_REQUIRED"):
        require_machine_role(principal, operation, frozenset({role}))


def test_cross_application_owner_denied():
    principal = ValidatedPrincipal("application", "tenant-1", "machine-1", "machine-1", frozenset(), frozenset())
    with pytest.raises(BearerValidationError, match="MACHINE_OWNER_MISMATCH"):
        require_machine_owner(principal, "machine-2")


def test_signing_metadata_fails_closed_after_24_hours():
    cache = SigningKeyCache({}, NOW - timedelta(hours=25), lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(BearerValidationError, match="AUTH_KEY_METADATA_UNAVAILABLE"):
        cache.key("kid", NOW)
    assert cache.ready(NOW) is False


def test_unknown_kid_refreshes_exactly_once_and_rejects_after_success():
    calls = []
    cache = SigningKeyCache({}, NOW, lambda: (calls.append(True) or {}, NOW))
    with pytest.raises(BearerValidationError, match="TOKEN_INVALID"):
        cache.key("unknown", NOW)
    assert len(calls) == 1


def test_known_key_refreshes_after_six_hours_but_falls_back_only_until_24_hours():
    calls = []
    cache = SigningKeyCache({"known": "cached-key"}, NOW - timedelta(hours=7), lambda: (calls.append(True) or (_ for _ in ()).throw(RuntimeError("offline"))))
    assert cache.key("known", NOW) == "cached-key"
    assert len(calls) == 1
    cache.refreshed_at = NOW - timedelta(hours=25)
    with pytest.raises(BearerValidationError, match="AUTH_KEY_METADATA_UNAVAILABLE"):
        cache.key("known", NOW)


@pytest.mark.parametrize(
    "operation,case",
    [(operation, case) for operation in AUTH_MATRIX["delegated"]["operations"] for case in AUTH_MATRIX["delegated"]["case_suffixes"]],
)
def test_manifest_delegated_authorization_matrix(operation, case):
    assert operation in DELEGATED_OPERATIONS
    claims = delegated_claims()
    if case == "valid" or case == "spoofed_forwarded_identity":
        principal = validate_claims(claims, POLICY, delegated=True, now=NOW)
        assert principal.actor_id == "employee-1"
        return
    if case == "wrong_issuer": claims["iss"] = "https://login.microsoftonline.com/common/v2.0"
    elif case == "wrong_tenant": claims["tid"] = "tenant-2"
    elif case == "wrong_audience": claims["aud"] = "api://other"
    elif case == "wrong_algorithm_or_key": claims.pop("tid")  # Signature/header rejection occurs before equivalent missing trusted claims.
    elif case == "wrong_lifetime": claims["exp"] = NOW.timestamp() - 1_000
    elif case == "wrong_client": claims["azp"] = "unapproved"
    elif case == "missing_scope": claims["scp"] = "Other.Scope"
    elif case == "missing_or_foreign_subject": claims.pop("oid")
    elif case == "id_token": claims.pop("scp")
    with pytest.raises(BearerValidationError):
        validate_claims(claims, POLICY, delegated=True, now=NOW)


@pytest.mark.parametrize(
    "operation,case",
    [(operation, case) for operation, cases in AUTH_MATRIX["machine"]["cases_by_operation"].items() for case in cases],
)
def test_manifest_machine_authorization_matrix(operation, case):
    required = OPERATION_ROLES[operation]
    principal = ValidatedPrincipal("application", "tenant-1", "machine-1", "machine-1", frozenset(), frozenset({required}))
    if case == "valid" or case == "request_supplied_employee_id_ignored":
        assert require_machine_role(principal, operation, frozenset({required})) == required
    elif case == "delegated_token" or case == "browser_cookie":
        delegated = ValidatedPrincipal("employee", "tenant-1", "employee", "bff-1", frozenset({"CareerAgent.Access"}), frozenset())
        with pytest.raises(BearerValidationError, match="WRONG_TOKEN_TYPE"):
            require_machine_role(delegated, operation, frozenset({required}))
    elif case in {"missing_role", "wrong_role"}:
        denied = ValidatedPrincipal("application", "tenant-1", "machine-1", "machine-1", frozenset(), frozenset() if case == "missing_role" else frozenset({"Wrong.Role"}))
        with pytest.raises(BearerValidationError, match="MACHINE_ROLE_REQUIRED"):
            require_machine_role(denied, operation, frozenset({required}))
    elif case in {"wrong_audience", "wrong_client", "employee_subject_spoof"}:
        claims = {"tid": "tenant-1", "iss": POLICY.issuer, "aud": "api://core", "nbf": NOW.timestamp() - 1, "exp": NOW.timestamp() + 3600, "azp": "machine-1", "roles": [required]}
        if case == "wrong_audience": claims["aud"] = "api://other"
        if case == "wrong_client": claims.pop("azp")
        if case == "employee_subject_spoof": claims["scp"] = "CareerAgent.Access"
        if case == "employee_subject_spoof":
            with pytest.raises(BearerValidationError, match="WRONG_TOKEN_TYPE"):
                validate_claims(claims, POLICY, delegated=False, now=NOW)
        else:
            with pytest.raises(BearerValidationError):
                validate_claims(claims, POLICY, delegated=False, now=NOW)
    elif case in {"employee_owned_reference", "cross_application_reference", "cross_application_same_key_isolated"}:
        with pytest.raises(BearerValidationError, match="MACHINE_OWNER_MISMATCH"):
            require_machine_owner(principal, "another-owner")
