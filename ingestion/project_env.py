"""Load repo-root `.env` for ingestion CLI modules (python -m ingestion.*)."""
from pathlib import Path

from dotenv import load_dotenv as _load_dotenv


def load_project_dotenv() -> None:
    root = Path(__file__).resolve().parent.parent
    _load_dotenv(root / ".env")
