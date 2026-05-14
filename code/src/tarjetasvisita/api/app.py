from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tarjetasvisita.config import load_settings
from tarjetasvisita.export import write_outlook_csv, write_vcf
from tarjetasvisita.ingest import ensure_project_dirs
from tarjetasvisita.llm.reconcile import extract_contact_entities_with_llm
from tarjetasvisita.pipeline.service import process_cards_folder, save_uploaded_files, write_contact_artifacts
from tarjetasvisita.schemas import ContactMethod
from tarjetasvisita.storage.sqlite import (
    fetch_contact_detail,
    fetch_contact_list,
    fetch_dashboard_summary,
    fetch_document_detail,
    initialize_database,
    load_contacts_from_db,
    load_ocr_markdown_for_document,
    persist_contact_entities,
    soft_delete_contact,
    update_contact_manual,
)


settings = load_settings()
ensure_project_dirs(settings)
initialize_database(settings.sqlite_db_path)

app = FastAPI(title="Tarjetas de Visita OCR API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    mode: str = Field(default="new_or_changed")


class ManualContactUpdateRequest(BaseModel):
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    job_title: str | None = None
    department: str | None = None
    website: str | None = None
    linkedin: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    country: str | None = None
    notes: str | None = None
    contact_methods: list[ContactMethod] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] | None = None
    extraction_version: str = "manual-edit-v1"


class ExportSelectionRequest(BaseModel):
    contact_ids: list[int] = Field(default_factory=list)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard/summary")
def dashboard_summary(low_confidence_threshold: float = Query(default=0.8, ge=0, le=1)) -> dict:
    return fetch_dashboard_summary(settings.sqlite_db_path, low_confidence_threshold=low_confidence_threshold)


@app.get("/api/contacts")
def contacts(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = None,
    max_confidence: float | None = Query(default=None, ge=0, le=1),
    has_warnings: bool | None = None,
) -> dict:
    return fetch_contact_list(
        settings.sqlite_db_path,
        limit=limit,
        offset=offset,
        search=search,
        max_confidence=max_confidence,
        has_warnings=has_warnings,
    )


@app.get("/api/contacts/{contact_id}")
def contact_detail(contact_id: int) -> dict:
    detail = fetch_contact_detail(settings.sqlite_db_path, contact_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return detail


@app.patch("/api/contacts/{contact_id}")
def update_contact(contact_id: int, payload: ManualContactUpdateRequest) -> dict:
    try:
        updated = update_contact_manual(
            settings.sqlite_db_path,
            contact_id,
            full_name=payload.full_name,
            first_name=payload.first_name,
            last_name=payload.last_name,
            company=payload.company,
            job_title=payload.job_title,
            department=payload.department,
            website=payload.website,
            linkedin=payload.linkedin,
            address=payload.address,
            city=payload.city,
            province=payload.province,
            postal_code=payload.postal_code,
            country=payload.country,
            notes=payload.notes,
            contact_methods=payload.contact_methods,
            confidence=payload.confidence,
            warnings=payload.warnings,
            extraction_version=payload.extraction_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    write_contact_artifacts(load_contacts_from_db(settings.sqlite_db_path), settings)
    return {"contact": updated.model_dump(mode="json"), "persisted": True}


@app.post("/api/contacts/{contact_id}/delete")
def delete_contact(contact_id: int) -> dict[str, bool]:
    try:
        soft_delete_contact(settings.sqlite_db_path, contact_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    write_contact_artifacts(load_contacts_from_db(settings.sqlite_db_path), settings)
    return {"deleted": True}


@app.post("/api/pipeline/process")
def pipeline_process(payload: ProcessRequest) -> dict:
    return process_cards_folder(settings, mode=payload.mode)


@app.post("/api/pipeline/upload")
async def pipeline_upload(
    files: list[UploadFile] = File(...),
    mode: str = Query(default="new_or_changed"),
) -> dict:
    saved = [(upload.filename or "uploaded.bin", await upload.read()) for upload in files]
    saved_names = save_uploaded_files(settings, saved)
    result = process_cards_folder(settings, mode=mode)
    return {"uploaded_files": saved_names, "processing_result": result}


@app.post("/api/pipeline/reextract/{document_id}")
def pipeline_reextract(document_id: str, persist: bool = False) -> dict:
    loaded = load_ocr_markdown_for_document(settings.sqlite_db_path, document_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Document not found")
    ocr_markdown, source_file = loaded
    if not ocr_markdown:
        raise HTTPException(status_code=400, detail="Document has no OCR markdown")
    contacts = extract_contact_entities_with_llm(
        ocr_markdown,
        document_id=document_id,
        source_file=source_file,
        settings=settings,
    )
    if persist:
        persist_contact_entities(settings.sqlite_db_path, contacts, extraction_version="manual-reextract-v1")
        write_contact_artifacts(load_contacts_from_db(settings.sqlite_db_path), settings)
    return {"contacts": [contact.model_dump(mode="json") for contact in contacts], "persisted": persist}


@app.get("/api/files/documents/{document_id}")
def get_document_file(document_id: str):
    detail = fetch_document_detail(settings.sqlite_db_path, document_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Document not found")
    source_path = detail.get("source_path")
    if not source_path:
        raise HTTPException(status_code=404, detail="Document source path not found")
    full_path = settings.project_root / source_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing on disk")
    return FileResponse(full_path)


@app.get("/api/exports/outlook.csv")
def export_outlook_csv():
    contacts = load_contacts_from_db(settings.sqlite_db_path)
    path = write_outlook_csv(contacts, settings.exports_dir / "outlook.csv")
    return FileResponse(path, media_type="text/csv", filename="outlook.csv")


@app.get("/api/exports/contacts.vcf")
def export_contacts_vcf():
    contacts = load_contacts_from_db(settings.sqlite_db_path)
    path = write_vcf(contacts, settings.exports_dir / "contacts.vcf")
    return FileResponse(path, media_type="text/vcard", filename="contacts.vcf")


@app.post("/api/exports/outlook.csv")
def export_selected_outlook_csv(payload: ExportSelectionRequest):
    contacts = load_contacts_from_db(settings.sqlite_db_path)
    path = write_outlook_csv(contacts, settings.exports_dir / "outlook.csv", contact_ids=payload.contact_ids)
    return FileResponse(path, media_type="text/csv", filename="outlook-selected.csv")


@app.post("/api/exports/contacts.vcf")
def export_selected_contacts_vcf(payload: ExportSelectionRequest):
    contacts = load_contacts_from_db(settings.sqlite_db_path)
    path = write_vcf(contacts, settings.exports_dir / "contacts.vcf", contact_ids=payload.contact_ids)
    return FileResponse(path, media_type="text/vcard", filename="contacts-selected.vcf")


frontend_dist = settings.code_dir / "web" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/")
    def root_index():
        return FileResponse(frontend_dist / "index.html")

else:

    @app.get("/")
    def root_index():
        return JSONResponse(
            {
                "message": "Frontend not built yet.",
                "next_steps": ["cd code/web", "npm run build"],
            }
        )
