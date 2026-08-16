from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.resend_adapter import ResendEmailAdapter
from app.core.config import Settings, get_settings
from app.db.database import SessionLocal


def get_session_factory() -> Callable[[], Session]:
    return SessionLocal


def get_resend_adapter(settings: Settings = Depends(get_settings)) -> ResendEmailAdapter:
    return ResendEmailAdapter(
        api_key=settings.resend_api_key_value,
        sender_address=settings.email_sender_address,
        sender_name=settings.email_sender_name,
        connect_timeout_seconds=settings.resend_connect_timeout_seconds,
        read_timeout_seconds=settings.resend_read_timeout_seconds,
    )
