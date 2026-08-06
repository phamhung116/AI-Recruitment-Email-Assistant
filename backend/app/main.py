from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agentRoutes import router as agent_router
from app.api.auditLogRoutes import router as audit_log_router
from app.api.candidateRoutes import router as candidate_router
from app.api.dashboardRoutes import router as dashboard_router
from app.api.emailHistoryRoutes import router as email_history_router
from app.api.emailQueueRoutes import router as email_queue_router
from app.api.emailTemplateRoutes import router as email_template_router
from app.api.routes import router
from app.core.config import get_settings
from app.db.database import Base, engine


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
    app.include_router(dashboard_router)
    app.include_router(candidate_router)
    app.include_router(email_template_router)
    app.include_router(email_queue_router)
    app.include_router(email_history_router)
    app.include_router(audit_log_router)
    app.include_router(agent_router)
    return app


app = create_app()


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
