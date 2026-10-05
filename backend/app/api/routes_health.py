import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.nlp.resources import check_nlp_resources

router = APIRouter(prefix="/api", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        logger.exception("Database health check failed")
        db_status = "error"
    nlp = check_nlp_resources()
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": db_status,
        "nlp_resources": nlp,
        "max_upload_mb": settings.max_upload_mb,
    }
