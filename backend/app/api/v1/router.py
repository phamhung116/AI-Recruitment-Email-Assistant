from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.drafts import router as drafts_router
from app.api.v1.send_operations import router as send_operations_router


router = APIRouter(prefix="/api/v1")
router.include_router(candidates_router)
router.include_router(drafts_router)
router.include_router(send_operations_router)
router.include_router(audit_router)
