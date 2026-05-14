from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Literal

from tarjetasvisita.config import Settings


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".tif", ".heif", ".txt"}


@dataclass(frozen=True)
class CardDocument:
    path: Path
    document_id: str
    extension: str


SelectionMode = Literal["new_or_changed", "all", "missing_ocr", "missing_entities"]


def is_supported_card_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def build_document_id(path: Path) -> str:
    resolved = path.resolve()
    identity = f"{resolved.name}:{resolved.stat().st_size}:{resolved.stat().st_mtime_ns}"
    return sha1(identity.encode("utf-8")).hexdigest()[:16]


def list_card_documents(directory: Path) -> list[CardDocument]:
    if not directory.exists():
        return []
    documents: list[CardDocument] = []
    for path in sorted(directory.iterdir()):
        if not is_supported_card_file(path):
            continue
        documents.append(CardDocument(path=path, document_id=build_document_id(path), extension=path.suffix.lower()))
    return documents


def ensure_project_dirs(settings: Settings) -> None:
    for path in [
        settings.raw_cards_dir,
        settings.ocr_output_dir,
        settings.entities_output_dir,
        settings.exports_dir,
        settings.reports_dir,
        settings.sqlite_db_path.parent,
    ]:
        path.mkdir(parents=True, exist_ok=True)
