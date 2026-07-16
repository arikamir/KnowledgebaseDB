"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from agent.errors import BoundaryViolationError, CareerAgentError, ValidationError
from api.errors import ApiProblem
from agent.logging import configure_logging
from agent.settings import AppSettings, load_settings
from api.route_helpers import AppContainer, build_container
from api.router import api_router
from api.middleware import correlation_middleware
from api.routes.health import router as health_router


def create_app(settings: AppSettings | None = None, container: AppContainer | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings.log_level)
    resolved_container = container or build_container(resolved_settings)

    app = FastAPI(title=resolved_settings.app_name)
    app.state.container = resolved_container
    app.state.identity_repository = resolved_container.identity_repository
    app.middleware("http")(correlation_middleware)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url=app.docs_url or "/docs")

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

    @app.exception_handler(RequestValidationError)
    def _handle_request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for error in exc.errors():
            location = error.get("loc", ())
            field = str(location[-1]) if location else "request"
            field_errors.setdefault(field, []).append(str(error.get("msg", "Invalid value")))
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        problem = ApiProblem(422, "VALIDATION_FAILED", "Request validation failed", retryable=False, field_errors=field_errors)
        return JSONResponse(problem.body(correlation_id), status_code=422, media_type="application/problem+json")

    app.include_router(api_router)
    app.include_router(health_router)
    return app


app = create_app()
