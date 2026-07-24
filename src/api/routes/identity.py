from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from api.routes.authz import employee_principal
from auth.bearer import ValidatedPrincipal
from storage.identity_repository import IdentityRepository

router = APIRouter()


class SessionBootstrapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    employee_id: str | None = None


@router.post("/identity/session-bootstrap", operation_id="bootstrapEmployeeSession", response_model=SessionBootstrapResponse)
def bootstrap_session(request: Request, principal: ValidatedPrincipal = Depends(employee_principal)) -> SessionBootstrapResponse:
    repository: IdentityRepository = request.app.state.identity_repository
    status, employee_id = repository.bootstrap_employee(principal.tenant_id, principal.actor_id)
    return SessionBootstrapResponse(status=status, employee_id=employee_id)
