"""Application error contract.

Every error leaves the API as RFC 9457 Problem Details with a machine-readable ``code``
(api.md §3, ADR-0010). Domain modules raise :class:`AppError` subclasses; a single set of
exception handlers renders them. Unexpected exceptions are logged with the request id and
rendered as ``INTERNAL_ERROR`` without any internal detail.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_id import get_request_id

PROBLEM_CONTENT_TYPE = "application/problem+json"
ERROR_TYPE_BASE = "https://fisikkati.app/errors/"

log = structlog.get_logger("app.errors")


class FieldError(BaseModel):
    """A validation problem attached to a specific input field."""

    field: str
    code: str
    message: str


class Problem(BaseModel):
    """RFC 9457 Problem Details document with Fi Sikkati extensions."""

    type: str
    title: str
    status: int
    code: str
    detail: str | None = None
    request_id: str | None = Field(default=None, serialization_alias="requestId")
    errors: list[FieldError] | None = None


class AppError(Exception):
    """Base class for all expected application errors.

    Subclasses set ``status_code``, ``code`` and ``title``; instances may add ``detail`` and
    field-level ``errors``.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "BAD_REQUEST"
    title: str = "Bad request"

    def __init__(
        self,
        detail: str | None = None,
        *,
        errors: Sequence[FieldError] | None = None,
        code: str | None = None,
        status_code: int | None = None,
        title: str | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        self.errors = list(errors) if errors else None
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        if title is not None:
            self.title = title

    def to_problem(self, request_id: str | None) -> Problem:
        return Problem(
            type=ERROR_TYPE_BASE + self.code.lower().replace("_", "-"),
            title=self.title,
            status=self.status_code,
            code=self.code,
            detail=self.detail,
            request_id=request_id,
            errors=self.errors,
        )


class ValidationAppError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "VALIDATION_ERROR"
    title = "Validation failed"


class UnauthenticatedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHENTICATED"
    title = "Authentication required"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    title = "Forbidden"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    title = "Not found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    title = "Conflict"


class RateLimitedError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMITED"
    title = "Too many requests"


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "SERVICE_UNAVAILABLE"
    title = "Service unavailable"


_HTTP_STATUS_CODES: dict[int, tuple[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: ("UNAUTHENTICATED", "Authentication required"),
    status.HTTP_403_FORBIDDEN: ("FORBIDDEN", "Forbidden"),
    status.HTTP_404_NOT_FOUND: ("NOT_FOUND", "Not found"),
    status.HTTP_405_METHOD_NOT_ALLOWED: ("METHOD_NOT_ALLOWED", "Method not allowed"),
    status.HTTP_409_CONFLICT: ("CONFLICT", "Conflict"),
    status.HTTP_413_CONTENT_TOO_LARGE: ("PAYLOAD_TOO_LARGE", "Payload too large"),
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: ("UNSUPPORTED_MEDIA_TYPE", "Unsupported media type"),
    status.HTTP_422_UNPROCESSABLE_CONTENT: ("VALIDATION_ERROR", "Validation failed"),
    status.HTTP_429_TOO_MANY_REQUESTS: ("RATE_LIMITED", "Too many requests"),
}


def _problem_response(problem: Problem, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(by_alias=True, exclude_none=True),
        media_type=PROBLEM_CONTENT_TYPE,
        headers=headers,
    )


def _field_errors_from_pydantic(raw_errors: Sequence[Any]) -> list[FieldError]:
    field_errors: list[FieldError] = []
    for err in raw_errors:
        location = [str(part) for part in err.get("loc", ()) if part not in ("body",)]
        field_errors.append(
            FieldError(
                field=".".join(location) or "body",
                code=str(err.get("type", "invalid")).upper(),
                message=str(err.get("msg", "Invalid value")),
            )
        )
    return field_errors


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 — registered only for AppError
    return _problem_response(exc.to_problem(get_request_id(request)))


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    problem = ValidationAppError(
        "One or more fields are invalid.",
        errors=_field_errors_from_pydantic(exc.errors()),
    ).to_problem(get_request_id(request))
    return _problem_response(problem)


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code, title = _HTTP_STATUS_CODES.get(exc.status_code, ("HTTP_ERROR", "Request failed"))
    detail = exc.detail if isinstance(exc.detail, str) else None
    problem = Problem(
        type=ERROR_TYPE_BASE + code.lower().replace("_", "-"),
        title=title,
        status=exc.status_code,
        code=code,
        detail=detail,
        request_id=get_request_id(request),
    )
    return _problem_response(problem, headers=dict(exc.headers) if exc.headers else None)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id(request)
    log.exception("unhandled_exception", request_id=request_id, exc_type=type(exc).__name__)
    problem = Problem(
        type=ERROR_TYPE_BASE + "internal-error",
        title="Internal server error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        detail="Something went wrong on our side. Please try again.",
        request_id=request_id,
    )
    return _problem_response(problem)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
