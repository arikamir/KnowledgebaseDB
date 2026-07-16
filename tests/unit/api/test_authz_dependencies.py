from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.routes.authz import employee_principal, machine_principal
from auth.bearer import BearerValidationError, ValidatedPrincipal


def request_for(validator_name, validator, authorization="Bearer token"):
    state = SimpleNamespace(**{validator_name: validator})
    return SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace(), headers={"authorization": authorization})


def test_employee_dependency_validates_bearer_before_exposing_principal():
    principal = ValidatedPrincipal("employee", "tenant", "owner", "bff", frozenset({"scope"}), frozenset())
    request = request_for("validate_delegated_token", lambda token: principal)
    assert employee_principal(request) is principal
    assert request.state.principal is principal


def test_invalid_machine_token_stops_at_dependency():
    request = request_for("validate_machine_token", lambda token: (_ for _ in ()).throw(BearerValidationError("MACHINE_TOKEN_INVALID")))
    with pytest.raises(HTTPException) as error:
        machine_principal(request)
    assert error.value.status_code == 401
