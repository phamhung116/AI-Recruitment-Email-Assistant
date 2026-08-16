"""Run an isolated synthetic backend for browser end-to-end tests."""

import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
E2E_ROOT = REPOSITORY_ROOT / ".staging" / "e2e"
E2E_DATABASE = E2E_ROOT / "recruitment-e2e.sqlite3"


def configure_environment() -> None:
    E2E_ROOT.mkdir(parents=True, exist_ok=True)
    if E2E_DATABASE.exists():
        E2E_DATABASE.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{E2E_DATABASE.as_posix()}"
    os.environ["BACKEND_CORS_ORIGINS"] = "http://127.0.0.1:14173"
    os.environ.pop("RESEND_API_KEY", None)


def main() -> None:
    configure_environment()

    import uvicorn

    from app.db.database import Base, engine
    from app.db.seed import seed

    Base.metadata.create_all(engine)
    seed()
    uvicorn.run("app.main:app", host="127.0.0.1", port=18000, log_level="warning")


if __name__ == "__main__":
    main()
