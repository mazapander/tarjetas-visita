from __future__ import annotations

from pathlib import Path
from typing import Any

from tarjetasvisita.config import Settings
from tarjetasvisita.export import write_outlook_csv, write_vcf
from tarjetasvisita.ingest import ensure_project_dirs, list_card_documents
from tarjetasvisita.llm.reconcile import extract_contact_entities_with_llm
from tarjetasvisita.ocr.mistral_ocr import (
    load_saved_ocr_results,
    ocr_from_text_file,
    run_mistral_ocr,
    save_ocr_result,
)
from tarjetasvisita.storage.sqlite import (
    initialize_database,
    load_contacts_from_db,
    persist_contact_entities,
    persist_documents,
    persist_ocr_results,
    select_documents_for_processing,
)


def process_cards_folder(settings: Settings, mode: str = "new_or_changed") -> dict[str, Any]:
    ensure_project_dirs(settings)
    initialize_database(settings.sqlite_db_path)

    documents = list_card_documents(settings.raw_cards_dir)
    documents_to_process = select_documents_for_processing(
        settings.sqlite_db_path,
        documents,
        settings.project_root,
        mode=mode,
    )
    persist_documents(settings.sqlite_db_path, documents, settings.project_root)

    cached = {result.document_id: result for result in load_saved_ocr_results(settings.ocr_output_dir)}
    ocr_results = []
    reused_saved_ocr = 0
    missing_ocr_documents: list[str] = []
    for document in documents_to_process:
        if document.extension == ".txt":
            result = ocr_from_text_file(document.path, document.document_id)
            save_ocr_result(result, settings.ocr_output_dir)
            ocr_results.append(result)
            continue
        if settings.has_mistral:
            result = run_mistral_ocr(document.path, document.document_id, settings.mistral_api_key or "")
            save_ocr_result(result, settings.ocr_output_dir)
            ocr_results.append(result)
            continue
        cached_result = cached.get(document.document_id)
        if cached_result is not None:
            ocr_results.append(cached_result)
            reused_saved_ocr += 1
        else:
            missing_ocr_documents.append(document.path.name)

    persist_ocr_results(settings.sqlite_db_path, ocr_results)

    contacts = []
    for result in ocr_results:
        contacts.extend(
            extract_contact_entities_with_llm(
                result.text,
                document_id=result.document_id,
                source_file=result.source_file,
                settings=settings,
            )
        )
    persist_contact_entities(settings.sqlite_db_path, contacts, extraction_version="v1")

    all_contacts = load_contacts_from_db(settings.sqlite_db_path)
    write_contact_artifacts(all_contacts, settings)

    return {
        "mode": mode,
        "total_discovered": len(documents),
        "selected_for_processing": len(documents_to_process),
        "ocr_processed": len(ocr_results),
        "reused_saved_ocr": reused_saved_ocr,
        "contacts_extracted": len(contacts),
        "total_contacts_persisted": len(all_contacts),
        "missing_ocr_documents": missing_ocr_documents,
    }


def save_uploaded_files(settings: Settings, files: list[tuple[str, bytes]]) -> list[str]:
    settings.raw_cards_dir.mkdir(parents=True, exist_ok=True)
    saved_names: list[str] = []
    for original_name, content in files:
        filename = Path(original_name).name
        destination = settings.raw_cards_dir / filename
        counter = 1
        while destination.exists():
            destination = settings.raw_cards_dir / f"{destination.stem}_{counter}{destination.suffix}"
            counter += 1
        destination.write_bytes(content)
        saved_names.append(destination.name)
    return saved_names


def write_contact_artifacts(contacts: list, settings: Settings) -> dict[str, str]:
    settings.entities_output_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = settings.entities_output_dir / "contacts.jsonl"
    jsonl_path.write_text(
        "\n".join(contact.model_dump_json() for contact in contacts),
        encoding="utf-8",
    )
    outlook_path = write_outlook_csv(contacts, settings.exports_dir / "outlook.csv")
    vcf_path = write_vcf(contacts, settings.exports_dir / "contacts.vcf")
    return {
        "contacts_jsonl": str(jsonl_path),
        "outlook_csv": str(outlook_path),
        "contacts_vcf": str(vcf_path),
    }
