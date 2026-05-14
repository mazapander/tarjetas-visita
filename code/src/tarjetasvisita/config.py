from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "code" / "pyproject.toml").exists():
            return candidate
        if candidate.name == "code" and (candidate / "pyproject.toml").exists():
            return candidate.parent
    return current


def resolve_project_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    code_dir: Path
    project_files_dir: Path
    sqlite_db_path: Path
    raw_cards_dir: Path
    ocr_output_dir: Path
    entities_output_dir: Path
    exports_dir: Path
    reports_dir: Path
    mistral_api_key: str | None
    llm_provider: str
    llm_api_key: str | None
    llm_base_url: str | None
    llm_model: str | None

    @property
    def has_mistral(self) -> bool:
        return bool(self.mistral_api_key)

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider.lower() != "disabled" and bool(self.llm_api_key)


def load_settings(project_root: Path | None = None) -> Settings:
    root = find_project_root(project_root)
    load_dotenv_file(root / ".env")

    project_files_dir = resolve_project_path(root, os.getenv("PROJECT_FILES_DIR") or "project_files")
    return Settings(
        project_root=root,
        code_dir=root / "code",
        project_files_dir=project_files_dir,
        sqlite_db_path=resolve_project_path(root, os.getenv("SQLITE_DB_PATH") or "project_files/app/tarjetasvisita.db"),
        raw_cards_dir=resolve_project_path(root, os.getenv("RAW_CARDS_DIR") or "project_files/raw/cards"),
        ocr_output_dir=resolve_project_path(root, os.getenv("OCR_OUTPUT_DIR") or "project_files/processed/ocr"),
        entities_output_dir=resolve_project_path(root, os.getenv("ENTITIES_OUTPUT_DIR") or "project_files/processed/entities"),
        exports_dir=resolve_project_path(root, os.getenv("EXPORTS_DIR") or "project_files/exports"),
        reports_dir=resolve_project_path(root, os.getenv("REPORTS_DIR") or "project_files/reports"),
        mistral_api_key=os.getenv("MISTRAL_API_KEY") or None,
        llm_provider=(os.getenv("LLM_PROVIDER") or "disabled").lower(),
        llm_api_key=os.getenv("LLM_API_KEY") or None,
        llm_base_url=os.getenv("LLM_BASE_URL") or None,
        llm_model=os.getenv("LLM_MODEL") or None,
    )
