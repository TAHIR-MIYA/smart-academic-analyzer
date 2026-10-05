"""Central, environment-driven configuration (no secrets are hard-coded)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Smart Academic Document Analyzer"
    app_version: str = "0.1.0"

    # Switching to MySQL later only requires changing this URL.
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'analyzer.db').as_posix()}"

    max_upload_mb: float = 10.0
    max_pdf_pages: int = 300
    min_text_chars: int = 20
    # Safety cap so one huge document cannot freeze the NLP pipeline on a laptop.
    max_analysis_chars: int = 500_000

    # Document-frequency table built from the training dataset (created by the Module 4 training script).
    reference_idf_path: Path = BASE_DIR / "app" / "ml" / "artifacts" / "reference_idf.json"

    log_level: str = "INFO"
    log_dir: Path = BASE_DIR / "logs"

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    return Settings()
