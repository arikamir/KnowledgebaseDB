"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent.errors import BoundaryViolationError, CareerAgentError, ValidationError
from agent.logging import configure_logging
from agent.settings import AppSettings, load_settings
from api.route_helpers import AppContainer, build_container
from api.router import api_router


def create_app(settings: AppSettings | None = None, container: AppContainer | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings.log_level)
    resolved_container = container or build_container(resolved_settings)

    app = FastAPI(title=resolved_settings.app_name)
    app.state.container = resolved_container

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(BoundaryViolationError)
    def _handle_boundary(_: Request, exc: BoundaryViolationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "category": exc.category},
        )

    @app.exception_handler(ValidationError)
    def _handle_validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(CareerAgentError)
    def _handle_agent_error(_: Request, exc: CareerAgentError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(api_router)
    return app


app = create_app()

