"""Dataset loading: one sub-folder per class, files are .txt, .pdf or .docx."""
import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.services.extraction import extract_text
from app.utils.errors import AppError, DatasetError

logger = logging.getLogger(__name__)

CLASS_NAMES = ["assignment", "notice", "question_paper", "project_report", "study_material"]
DISPLAY_NAMES = {
    "assignment": "Assignment",
    "notice": "Notice",
    "question_paper": "Question Paper",
    "project_report": "Project Report",
    "study_material": "Study Material",
}
_SUFFIX_TYPES = {".txt": "txt", ".pdf": "pdf", ".docx": "docx"}


@dataclass(frozen=True)
class Sample:
    text: str
    label: str
    name: str


def load_folder_dataset(root: Path, min_per_class: int = 1, require_all_classes: bool = True) -> list[Sample]:
    """Read root/<class>/<file>. Unreadable or empty files are skipped with a warning."""
    root = Path(root)
    if not root.is_dir():
        raise DatasetError(f"Dataset folder not found: {root}")

    extractor_settings = Settings(min_text_chars=20)
    samples: list[Sample] = []
    for label in CLASS_NAMES:
        folder = root / label
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            file_type = _SUFFIX_TYPES.get(path.suffix.lower())
            if file_type is None or not path.is_file():
                continue
            try:
                result = extract_text(file_type, path.read_bytes(), extractor_settings)
            except AppError as exc:
                logger.warning("Skipping %s: %s", path, exc.message)
                continue
            samples.append(Sample(result.text, label, f"{label}/{path.name}"))

    counts = {label: sum(1 for s in samples if s.label == label) for label in CLASS_NAMES}
    if require_all_classes:
        short = [label for label, n in counts.items() if n < min_per_class]
        if short:
            raise DatasetError(
                f"Each class needs at least {min_per_class} document(s); too few for: {', '.join(short)} (counts: {counts})"
            )
    if not samples:
        raise DatasetError(f"No usable documents found in {root}")
    return samples


def dataset_exists(root: Path) -> bool:
    try:
        return bool(load_folder_dataset(Path(root), require_all_classes=False))
    except DatasetError:
        return False
