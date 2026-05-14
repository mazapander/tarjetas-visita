from pathlib import Path

from tarjetasvisita.config import Settings
from tarjetasvisita.export import write_outlook_csv
from tarjetasvisita.pipeline.service import process_cards_folder
from tarjetasvisita.storage.sqlite import load_contacts_from_db, soft_delete_contact


def make_settings(project_root: Path) -> Settings:
    return Settings(
        project_root=project_root,
        code_dir=project_root / "code",
        project_files_dir=project_root / "project_files",
        sqlite_db_path=project_root / "project_files/app/tarjetasvisita.db",
        raw_cards_dir=project_root / "project_files/raw/cards",
        ocr_output_dir=project_root / "project_files/processed/ocr",
        entities_output_dir=project_root / "project_files/processed/entities",
        exports_dir=project_root / "project_files/exports",
        reports_dir=project_root / "project_files/reports",
        mistral_api_key=None,
        llm_provider="disabled",
        llm_api_key=None,
        llm_base_url=None,
        llm_model=None,
    )


def test_pipeline_processes_text_card_into_project_files(tmp_path: Path):
    settings = make_settings(tmp_path)
    settings.raw_cards_dir.mkdir(parents=True)
    (settings.raw_cards_dir / "card.txt").write_text(
        """ANDER FERNANDEZ
ACME SOLUTIONS S.L.
Director Comercial
ander@acme.com
+34 600 123 456
www.acme.com
""",
        encoding="utf-8",
    )

    result = process_cards_folder(settings)

    assert result["total_discovered"] == 1
    assert result["ocr_processed"] == 1
    assert result["contacts_extracted"] == 1
    assert settings.sqlite_db_path.exists()
    assert (settings.exports_dir / "outlook.csv").exists()
    assert (settings.exports_dir / "contacts.vcf").exists()
    contacts = load_contacts_from_db(settings.sqlite_db_path)
    assert len(contacts) == 1
    assert contacts[0].company == "ACME SOLUTIONS S.L."


def test_soft_delete_hides_contact_and_export_can_filter_selection(tmp_path: Path):
    settings = make_settings(tmp_path)
    settings.raw_cards_dir.mkdir(parents=True)
    (settings.raw_cards_dir / "card.txt").write_text(
        """ANDER FERNANDEZ
ACME SOLUTIONS S.L.
ander@acme.com
+34 600 123 456
""",
        encoding="utf-8",
    )

    process_cards_folder(settings)
    contacts = load_contacts_from_db(settings.sqlite_db_path)
    assert len(contacts) == 1
    contact_id = contacts[0].contact_id
    assert contact_id is not None

    filtered_csv = settings.exports_dir / "selected.csv"
    write_outlook_csv(contacts, filtered_csv, contact_ids=[contact_id])
    assert "ANDER FERNANDEZ" in filtered_csv.read_text(encoding="utf-8-sig")

    soft_delete_contact(settings.sqlite_db_path, contact_id)
    visible_contacts = load_contacts_from_db(settings.sqlite_db_path)
    assert visible_contacts == []
