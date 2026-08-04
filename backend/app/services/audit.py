from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(db: Session, action: str, entity_type: str | None = None, entity_id: int | None = None, actor: str = "demo_hr", metadata: dict | None = None) -> None:
    db.add(
        AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata_json=metadata or {},
        )
    )
