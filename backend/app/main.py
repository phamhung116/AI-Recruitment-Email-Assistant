from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.v1.errors import (
    SERVICE_ERRORS,
    service_error_handler,
    v1_http_error_handler,
    v1_validation_error_handler,
)
from app.api.v1.router import router as v1_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Recruitment Email Assistant API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(v1_router)
    for error_type in SERVICE_ERRORS:
        app.add_exception_handler(error_type, service_error_handler)
    app.add_exception_handler(HTTPException, v1_http_error_handler)
    app.add_exception_handler(RequestValidationError, v1_validation_error_handler)
    return app


app = create_app()
