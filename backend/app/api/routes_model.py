import json
import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas.document import ErrorResponse
from app.utils.errors import ModelNotTrainedError

router = APIRouter(prefix="/api/model", tags=["model"])
logger = logging.getLogger(__name__)


@router.get("/metrics", response_model=dict[str, Any], responses={503: {"model": ErrorResponse}})
def get_metrics(settings: Settings = Depends(get_settings)):
    """Training/evaluation results written by `python -m app.ml.train` (nothing is computed here)."""
    try:
        return json.loads(settings.metrics_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Metrics file unavailable: %s", exc)
        raise ModelNotTrainedError(
            "No training metrics were found.", details={"fix": "python -m app.ml.train"}
        ) from exc
