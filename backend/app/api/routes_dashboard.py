from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.db.models import Document
from app.ml.dataset import DISPLAY_NAMES
from app.schemas.analysis import DashboardResponse
from app.services import analysis_store, model_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardResponse)
def dashboard_summary(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Numbers for the dashboard page. Class counts come from saved predictions, not from evaluation."""
    total = db.scalar(select(func.count(Document.id))) or 0
    words = db.scalar(select(func.coalesce(func.sum(Document.word_count), 0))) or 0
    by_type = dict(db.execute(select(Document.file_type, func.count(Document.id)).group_by(Document.file_type)).all())
    analysed = analysis_store.analysed_document_ids(db)
    stored = analysis_store.all_stored(db)
    classified = [a["classification"] for a in stored if a.get("classification")]
    counts = Counter(c["label"] for c in classified)
    recent = db.scalars(select(Document).order_by(Document.created_at.desc(), Document.id.desc()).limit(5)).all()
    return {
        "total_documents": total,
        "analyzed_documents": len(analysed),
        "total_words": int(words),
        "by_file_type": by_type,
        "class_distribution": [{"label": k, "display_name": DISPLAY_NAMES.get(k, k), "count": v}
                               for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))],
        "uncertain_predictions": sum(1 for c in classified if not c["is_confident"]),
        "recent_documents": [{"id": d.id, "filename": d.original_filename, "file_type": d.file_type,
                              "word_count": d.word_count, "analyzed": d.id in analysed,
                              "created_at": d.created_at.isoformat(timespec="seconds")} for d in recent],
        "model": model_service.model_summary(settings),
    }
