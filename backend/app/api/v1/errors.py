from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.adapters.resend_adapter import ResendConfigurationError
from app.services.draft_service import DraftServiceError
from app.services.send_orchestrator import SendOrchestratorError


SERVICE_ERRORS = (DraftServiceError, SendOrchestratorError, ResendConfigurationError)


async def service_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error_code = getattr(exc, "error_code", "EMAIL_PROVIDER_NOT_CONFIGURED")
    message = getattr(exc, "message", str(exc))
    status_code = _status_for_error(error_code)
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid4()),
        },
    )


async def v1_http_error_handler(request: Request, exc: HTTPException):
    if not request.url.path.startswith("/api/v1"):
        return await http_exception_handler(request, exc)
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    return _error_response(
        status_code=exc.status_code,
        error_code=_http_error_code(exc.status_code),
        message=message,
        details={} if isinstance(exc.detail, str) else {"detail": exc.detail},
    )


async def v1_validation_error_handler(request: Request, exc: RequestValidationError):
    if not request.url.path.startswith("/api/v1"):
        return await request_validation_exception_handler(request, exc)
    details = {
        "fields": [
            {
                "location": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
    }
    return _error_response(
        status_code=422,
        error_code="REQUEST_VALIDATION_FAILED",
        message="One or more request fields are invalid.",
        details=details,
    )


def _error_response(
    *, status_code: int, error_code: str, message: str, details: dict
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid4()),
        },
    )


def _http_error_code(status_code: int) -> str:
    return {
        404: "RESOURCE_NOT_FOUND",
        409: "RESOURCE_CONFLICT",
        422: "REQUEST_VALIDATION_FAILED",
    }.get(status_code, "REQUEST_FAILED")


def _status_for_error(error_code: str) -> int:
    if error_code.endswith("_NOT_FOUND") or error_code in {
        "APPLICATION_NOT_FOUND",
        "SEND_OPERATION_STATE_MISSING",
    }:
        return 404
    if error_code in {
        "CORRECTION_NOT_REQUIRED",
        "ACTIVE_CORRECTION_EXISTS",
        "IDEMPOTENCY_WINDOW_EXPIRED",
        "SEND_OPERATION_NOT_RETRYABLE",
        "DELIVERY_UNKNOWN_REQUIRED",
    }:
        return 409
    return 422
