"""Safe correlation and problem-response middleware."""

from __future__ import annotations

from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from api.errors import ApiProblem


async def correlation_middleware(request: Request, call_next):
    supplied = request.headers.get("x-correlation-id", "")
    correlation_id = supplied if 1 <= len(supplied) <= 128 and supplied.replace("-", "").isalnum() else uuid4().hex
    request.state.correlation_id = correlation_id
    try:
        response = await call_next(request)
    except ApiProblem as problem:
        headers = {"X-Correlation-ID": correlation_id}
        if problem.retry_after is not None:
            headers["Retry-After"] = str(problem.retry_after)
        return JSONResponse(problem.body(correlation_id), status_code=problem.status, media_type="application/problem+json", headers=headers)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
