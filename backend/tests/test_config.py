from pydantic import SecretStr

from app.core.config import Settings


def test_settings_have_safe_runtime_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.backend_host == "0.0.0.0"
    assert settings.backend_port == 8000
    assert settings.environment == "development"
    assert settings.email_sender_address == "onboarding@resend.dev"
    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_resend_api_key_is_secret_and_normalized() -> None:
    settings = Settings(_env_file=None, resend_api_key="  re_test_value  ")

    assert isinstance(settings.resend_api_key, SecretStr)
    assert settings.resend_api_key_value == "re_test_value"
    assert "re_test_value" not in repr(settings)


def test_blank_resend_api_key_is_not_configured() -> None:
    settings = Settings(_env_file=None, resend_api_key="   ")

    assert settings.resend_api_key_value is None
