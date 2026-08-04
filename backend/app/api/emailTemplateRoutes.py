from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.constants.messages import TEMPLATE_NOT_FOUND_MESSAGE
from app.db.database import get_db
from app.models import EmailTemplate
from app.schemas import EmailTemplateCreate, EmailTemplateRead, EmailTemplateUpdate

router = APIRouter(prefix="/email-templates", tags=["Email Templates"])
DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[EmailTemplateRead])
def list_templates(
    db: DbDep,
) -> list[EmailTemplate]:
    return db.query(EmailTemplate).order_by(EmailTemplate.email_type.asc()).all()


@router.post("", response_model=EmailTemplateRead)
def create_template(
    db: DbDep,
    payload: EmailTemplateCreate,
) -> EmailTemplate:
    template = EmailTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.patch("/{template_id}", response_model=EmailTemplateRead)
def update_template(
    db: DbDep,
    template_id: int,
    payload: EmailTemplateUpdate,
) -> EmailTemplate:
    template = find_template_or_raise(db, template_id)

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field_name, value)

    db.commit()
    db.refresh(template)

    return template


@router.delete("/{template_id}")
def delete_template(
    db: DbDep,
    template_id: int,
) -> dict[str, bool]:
    template = find_template_or_raise(db, template_id)
    db.delete(template)
    db.commit()

    return {"deleted": True}


def find_template_or_raise(
    db: Session,
    template_id: int,
) -> EmailTemplate:
    template = db.get(EmailTemplate, template_id)

    if not template:
        raise HTTPException(status_code=404, detail=TEMPLATE_NOT_FOUND_MESSAGE)

    return template
