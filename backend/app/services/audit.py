from sqlalchemy.orm import Session

from app.models import ActionOutcome, AuditLog


def log_action(db: Session, action: str, entity_type: str | None = None, entity_id: int | None = None, actor: str = "demo_hr", metadata: dict | None = None) -> None:
    db.add(
        AuditLog(
            event_name=action,
            entity_type=entity_type or "SYSTEM",
            entity_id=str(entity_id) if entity_id is not None else "bulk",
            actor=actor,
            action_outcome=ActionOutcome.SUCCESS.value,
            payload_json=metadata or {},
        )
    )
