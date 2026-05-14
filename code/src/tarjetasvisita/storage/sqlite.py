from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
import json
from pathlib import Path
import sqlite3
from typing import Any

from tarjetasvisita.ingest import CardDocument, SelectionMode
from tarjetasvisita.normalization import normalize_text
from tarjetasvisita.schemas import ContactEntities, ContactMethod, OcrResult


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_path TEXT,
    file_hash TEXT,
    mime_type TEXT,
    file_size_bytes INTEGER,
    ingested_at TEXT NOT NULL,
    deleted_at TEXT,
    document_status TEXT NOT NULL DEFAULT 'discovered'
);

CREATE TABLE IF NOT EXISTS ocr_results (
    ocr_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL UNIQUE,
    ocr_provider TEXT NOT NULL,
    ocr_model TEXT NOT NULL,
    ocr_text TEXT,
    ocr_markdown TEXT,
    raw_response_json TEXT NOT NULL,
    average_confidence REAL,
    pages_processed INTEGER,
    processed_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS contact_entities (
    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    contact_index INTEGER NOT NULL DEFAULT 0,
    full_name TEXT,
    first_name TEXT,
    last_name TEXT,
    company TEXT,
    company_normalized TEXT,
    job_title TEXT,
    department TEXT,
    website TEXT,
    linkedin TEXT,
    address TEXT,
    city TEXT,
    province TEXT,
    postal_code TEXT,
    country TEXT,
    notes TEXT,
    extraction_method TEXT NOT NULL,
    extraction_version TEXT NOT NULL,
    annotation_status TEXT NOT NULL DEFAULT 'system_extracted',
    reviewed_at TEXT,
    confidence REAL,
    warnings_json TEXT,
    visible INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE(document_id, contact_index),
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS contact_methods (
    method_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    document_id TEXT NOT NULL,
    method_type TEXT NOT NULL,
    label TEXT,
    raw_value TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(contact_id, method_type, normalized_value),
    FOREIGN KEY (contact_id) REFERENCES contact_entities(contact_id),
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_source_file ON documents(source_file);
CREATE INDEX IF NOT EXISTS idx_contact_entities_document ON contact_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_contact_entities_company ON contact_entities(company_normalized);
CREATE INDEX IF NOT EXISTS idx_contact_entities_name ON contact_entities(full_name);
CREATE INDEX IF NOT EXISTS idx_contact_methods_normalized ON contact_methods(method_type, normalized_value);
"""


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path) -> None:
    with connect_db(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(contact_entities)").fetchall()}
        if "visible" not in columns:
            connection.execute("ALTER TABLE contact_entities ADD COLUMN visible INTEGER NOT NULL DEFAULT 1")
            connection.execute("UPDATE contact_entities SET visible = CASE WHEN deleted_at IS NULL THEN 1 ELSE 0 END")
        connection.commit()


def file_sha1(path: Path) -> str:
    return sha1(path.read_bytes()).hexdigest()


def mime_type_from_path(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".heif": "image/heif",
        ".txt": "text/plain",
    }.get(path.suffix.lower(), "application/octet-stream")


def select_documents_for_processing(
    db_path: Path,
    documents: list[CardDocument],
    project_root: Path,
    mode: SelectionMode = "new_or_changed",
) -> list[CardDocument]:
    if mode == "all":
        return documents
    if not documents:
        return []

    initialize_database(db_path)
    with connect_db(db_path) as connection:
        existing = {
            row["source_path"]: row
            for row in connection.execute(
                """
                SELECT
                    d.source_path,
                    d.file_hash,
                    CASE WHEN o.document_id IS NOT NULL THEN 1 ELSE 0 END AS has_ocr,
                    CASE WHEN ce.document_id IS NOT NULL THEN 1 ELSE 0 END AS has_entities
                FROM documents d
                LEFT JOIN ocr_results o ON o.document_id = d.document_id
                LEFT JOIN contact_entities ce ON ce.document_id = d.document_id AND ce.deleted_at IS NULL
                WHERE d.deleted_at IS NULL
                """
            ).fetchall()
        }

    selected: list[CardDocument] = []
    for document in documents:
        resolved = document.path.resolve()
        source_path = str(resolved.relative_to(project_root.resolve()))
        row = existing.get(source_path)
        if row is None:
            selected.append(document)
            continue
        has_changed = file_sha1(resolved) != row["file_hash"]
        has_ocr = bool(row["has_ocr"])
        has_entities = bool(row["has_entities"])
        if mode == "new_or_changed" and (has_changed or not has_ocr or not has_entities):
            selected.append(document)
        elif mode == "missing_ocr" and (has_changed or not has_ocr):
            selected.append(document)
        elif mode == "missing_entities" and (has_changed or not has_entities):
            selected.append(document)
    return selected


def persist_documents(db_path: Path, documents: list[CardDocument], project_root: Path) -> None:
    if not documents:
        return
    with connect_db(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        for document in documents:
            resolved = document.path.resolve()
            connection.execute(
                """
                INSERT INTO documents (
                    document_id, source_file, source_path, file_hash, mime_type, file_size_bytes, ingested_at, document_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    source_file=excluded.source_file,
                    source_path=excluded.source_path,
                    file_hash=excluded.file_hash,
                    mime_type=excluded.mime_type,
                    file_size_bytes=excluded.file_size_bytes,
                    deleted_at=NULL
                """,
                (
                    document.document_id,
                    document.path.name,
                    str(resolved.relative_to(project_root.resolve())),
                    file_sha1(resolved),
                    mime_type_from_path(resolved),
                    resolved.stat().st_size,
                    utc_now_iso(),
                    "discovered",
                ),
            )
        connection.commit()


def persist_ocr_results(db_path: Path, results: list[OcrResult]) -> None:
    if not results:
        return
    with connect_db(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        for result in results:
            raw = result.raw_response
            pages_processed = (raw.get("usage_info") or {}).get("pages_processed")
            connection.execute(
                """
                INSERT INTO ocr_results (
                    document_id, ocr_provider, ocr_model, ocr_text, ocr_markdown, raw_response_json,
                    average_confidence, pages_processed, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    ocr_provider=excluded.ocr_provider,
                    ocr_model=excluded.ocr_model,
                    ocr_text=excluded.ocr_text,
                    ocr_markdown=excluded.ocr_markdown,
                    raw_response_json=excluded.raw_response_json,
                    average_confidence=excluded.average_confidence,
                    pages_processed=excluded.pages_processed,
                    processed_at=excluded.processed_at
                """,
                (
                    result.document_id,
                    result.provider,
                    result.model,
                    result.text,
                    result.text,
                    json.dumps(raw, ensure_ascii=True),
                    average_page_confidence(raw),
                    pages_processed,
                    utc_now_iso(),
                ),
            )
            connection.execute("UPDATE documents SET document_status = ? WHERE document_id = ?", ("ocr_processed", result.document_id))
        connection.commit()


def persist_contact_entities(
    db_path: Path,
    contacts: list[ContactEntities],
    extraction_version: str = "v1",
    replace_documents: bool = True,
) -> None:
    if not contacts:
        return
    with connect_db(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        if replace_documents:
            for document_id in {contact.document_id for contact in contacts}:
                old_ids = [row[0] for row in connection.execute("SELECT contact_id FROM contact_entities WHERE document_id = ?", (document_id,)).fetchall()]
                for contact_id in old_ids:
                    connection.execute("DELETE FROM contact_methods WHERE contact_id = ?", (contact_id,))
                connection.execute("DELETE FROM contact_entities WHERE document_id = ?", (document_id,))

        for contact in contacts:
            annotation_status = annotation_status_from_method(contact.extraction_method)
            reviewed_at = utc_now_iso() if annotation_status != "system_extracted" else None
            cursor = connection.execute(
                """
                INSERT INTO contact_entities (
                    document_id, contact_index, full_name, first_name, last_name, company, company_normalized,
                    job_title, department, website, linkedin, address, city, province, postal_code, country, notes,
                    extraction_method, extraction_version, annotation_status, reviewed_at, confidence, warnings_json, created_at, visible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contact.document_id,
                    contact.contact_index,
                    contact.full_name,
                    contact.first_name,
                    contact.last_name,
                    contact.company,
                    normalize_text(contact.company) or None,
                    contact.job_title,
                    contact.department,
                    contact.website,
                    contact.linkedin,
                    contact.address,
                    contact.city,
                    contact.province,
                    contact.postal_code,
                    contact.country,
                    contact.notes,
                    contact.extraction_method or "unknown",
                    extraction_version,
                    annotation_status,
                    reviewed_at,
                    contact.confidence,
                    json.dumps(contact.warnings, ensure_ascii=True),
                    utc_now_iso(),
                    1,
                ),
            )
            contact_id = int(cursor.lastrowid)
            _persist_contact_methods(connection, contact_id, contact.document_id, contact.contact_methods)
            connection.execute("UPDATE documents SET document_status = ? WHERE document_id = ?", ("entities_extracted", contact.document_id))
        connection.commit()


def _persist_contact_methods(
    connection: sqlite3.Connection,
    contact_id: int,
    document_id: str,
    methods: list[ContactMethod],
) -> None:
    for method in methods:
        connection.execute(
            """
            INSERT INTO contact_methods (
                contact_id, document_id, method_type, label, raw_value, normalized_value, is_primary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(contact_id, method_type, normalized_value) DO UPDATE SET
                label=excluded.label,
                raw_value=excluded.raw_value,
                is_primary=excluded.is_primary
            """,
            (
                contact_id,
                document_id,
                method.method_type,
                method.label,
                method.raw_value,
                method.normalized_value,
                1 if method.is_primary else 0,
                utc_now_iso(),
            ),
        )


def load_contacts_from_db(db_path: Path, include_deleted: bool = False) -> list[ContactEntities]:
    where = "" if include_deleted else "WHERE ce.deleted_at IS NULL AND ce.visible = 1"
    with connect_db(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT ce.*, d.source_file
            FROM contact_entities ce
            JOIN documents d ON d.document_id = ce.document_id
            {where}
            ORDER BY ce.created_at DESC, ce.contact_id DESC
            """
        ).fetchall()
        methods_by_contact = _load_methods_by_contact(connection, [row["contact_id"] for row in rows])
    return [_contact_from_row(row, methods_by_contact.get(row["contact_id"], [])) for row in rows]


def load_contact_by_id(db_path: Path, contact_id: int) -> ContactEntities | None:
    with connect_db(db_path) as connection:
        row = connection.execute(
            """
            SELECT ce.*, d.source_file
            FROM contact_entities ce
            JOIN documents d ON d.document_id = ce.document_id
            WHERE ce.contact_id = ? AND ce.deleted_at IS NULL AND ce.visible = 1
            """,
            (contact_id,),
        ).fetchone()
        if row is None:
            return None
        methods = _load_methods_by_contact(connection, [contact_id]).get(contact_id, [])
    return _contact_from_row(row, methods)


def fetch_dashboard_summary(db_path: Path, low_confidence_threshold: float = 0.8) -> dict[str, Any]:
    initialize_database(db_path)
    with connect_db(db_path) as connection:
        total_documents = connection.execute("SELECT COUNT(*) FROM documents WHERE deleted_at IS NULL").fetchone()[0]
        total_contacts = connection.execute("SELECT COUNT(*) FROM contact_entities WHERE deleted_at IS NULL AND visible = 1").fetchone()[0]
        low_confidence = connection.execute(
            "SELECT COUNT(*) FROM contact_entities WHERE deleted_at IS NULL AND visible = 1 AND (confidence IS NULL OR confidence < ?)",
            (low_confidence_threshold,),
        ).fetchone()[0]
        with_warnings = connection.execute(
            "SELECT COUNT(*) FROM contact_entities WHERE deleted_at IS NULL AND visible = 1 AND warnings_json IS NOT NULL AND warnings_json != '[]'"
        ).fetchone()[0]
        without_email = connection.execute(
            """
            SELECT COUNT(*)
            FROM contact_entities ce
            WHERE ce.deleted_at IS NULL AND ce.visible = 1 AND NOT EXISTS (
                SELECT 1 FROM contact_methods cm WHERE cm.contact_id = ce.contact_id AND cm.method_type = 'email'
            )
            """
        ).fetchone()[0]
        without_phone = connection.execute(
            """
            SELECT COUNT(*)
            FROM contact_entities ce
            WHERE ce.deleted_at IS NULL AND ce.visible = 1 AND NOT EXISTS (
                SELECT 1 FROM contact_methods cm
                WHERE cm.contact_id = ce.contact_id AND cm.method_type IN ('phone', 'mobile')
            )
            """
        ).fetchone()[0]
        duplicate_methods = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT method_type, normalized_value
                FROM contact_methods
                GROUP BY method_type, normalized_value
                HAVING COUNT(DISTINCT contact_id) > 1
            )
            """
        ).fetchone()[0]
    return {
        "total_documents": total_documents,
        "total_contacts": total_contacts,
        "low_confidence_contacts": low_confidence,
        "contacts_with_warnings": with_warnings,
        "contacts_without_email": without_email,
        "contacts_without_phone": without_phone,
        "possible_duplicates": duplicate_methods,
        "low_confidence_threshold": low_confidence_threshold,
    }


def fetch_contact_list(
    db_path: Path,
    *,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
    max_confidence: float | None = None,
    has_warnings: bool | None = None,
) -> dict[str, Any]:
    where_clauses = ["ce.deleted_at IS NULL", "ce.visible = 1"]
    params: list[Any] = []
    if search:
        where_clauses.append(
            """
            (
                ce.full_name LIKE ? OR ce.company LIKE ? OR ce.job_title LIKE ? OR d.source_file LIKE ?
                OR EXISTS (
                    SELECT 1 FROM contact_methods cm
                    WHERE cm.contact_id = ce.contact_id AND cm.normalized_value LIKE ?
                )
            )
            """
        )
        term = f"%{search}%"
        params.extend([term, term, term, term, term])
    if max_confidence is not None:
        where_clauses.append("(ce.confidence IS NULL OR ce.confidence <= ?)")
        params.append(max_confidence)
    if has_warnings is True:
        where_clauses.append("ce.warnings_json IS NOT NULL AND ce.warnings_json != '[]'")
    elif has_warnings is False:
        where_clauses.append("(ce.warnings_json IS NULL OR ce.warnings_json = '[]')")

    where_sql = f"WHERE {' AND '.join(where_clauses)}"
    with connect_db(db_path) as connection:
        total_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM contact_entities ce
            JOIN documents d ON d.document_id = ce.document_id
            {where_sql}
            """,
            params,
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT ce.*, d.source_file
            FROM contact_entities ce
            JOIN documents d ON d.document_id = ce.document_id
            {where_sql}
            ORDER BY ce.created_at DESC, ce.contact_id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        methods_by_contact = _load_methods_by_contact(connection, [row["contact_id"] for row in rows])
    return {
        "total_count": total_count,
        "items": [_contact_to_api(_contact_from_row(row, methods_by_contact.get(row["contact_id"], []))) for row in rows],
    }


def fetch_contact_detail(db_path: Path, contact_id: int) -> dict[str, Any] | None:
    with connect_db(db_path) as connection:
        row = connection.execute(
            """
            SELECT
                ce.*, d.source_file, d.source_path, d.ingested_at, d.document_status,
                o.ocr_provider, o.ocr_model, o.ocr_markdown, o.average_confidence, o.pages_processed, o.processed_at
            FROM contact_entities ce
            JOIN documents d ON d.document_id = ce.document_id
            LEFT JOIN ocr_results o ON o.document_id = ce.document_id
            WHERE ce.contact_id = ? AND ce.deleted_at IS NULL AND ce.visible = 1
            """,
            (contact_id,),
        ).fetchone()
        if row is None:
            return None
        methods = _load_methods_by_contact(connection, [contact_id]).get(contact_id, [])
    contact = _contact_from_row(row, methods)
    return {
        "contact": _contact_to_api(contact),
        "document": {
            "document_id": row["document_id"],
            "source_file": row["source_file"],
            "source_path": row["source_path"],
            "uploaded_at": row["ingested_at"],
            "document_status": row["document_status"],
            "image_url": f"/api/files/documents/{row['document_id']}",
        },
        "ocr": {
            "provider": row["ocr_provider"],
            "model": row["ocr_model"],
            "markdown": row["ocr_markdown"] or "",
            "average_confidence": row["average_confidence"],
            "pages_processed": row["pages_processed"],
            "processed_at": row["processed_at"],
        },
    }


def fetch_document_detail(db_path: Path, document_id: str) -> dict[str, Any] | None:
    with connect_db(db_path) as connection:
        row = connection.execute("SELECT * FROM documents WHERE document_id = ? AND deleted_at IS NULL", (document_id,)).fetchone()
    return dict(row) if row else None


def load_ocr_markdown_for_document(db_path: Path, document_id: str) -> tuple[str, str | None] | None:
    with connect_db(db_path) as connection:
        row = connection.execute(
            """
            SELECT d.source_file, o.ocr_markdown
            FROM documents d
            LEFT JOIN ocr_results o ON o.document_id = d.document_id
            WHERE d.document_id = ? AND d.deleted_at IS NULL
            """,
            (document_id,),
        ).fetchone()
    if row is None:
        return None
    return row["ocr_markdown"] or "", row["source_file"]


def update_contact_manual(
    db_path: Path,
    contact_id: int,
    *,
    full_name: str | None,
    first_name: str | None,
    last_name: str | None,
    company: str | None,
    job_title: str | None,
    department: str | None,
    website: str | None,
    linkedin: str | None,
    address: str | None,
    city: str | None,
    province: str | None,
    postal_code: str | None,
    country: str | None,
    notes: str | None,
    contact_methods: list[ContactMethod],
    confidence: float | None,
    warnings: list[str] | None,
    extraction_version: str,
) -> ContactEntities:
    existing = load_contact_by_id(db_path, contact_id)
    if existing is None:
        raise ValueError(f"Contact not found for contact_id={contact_id}")
    with connect_db(db_path) as connection:
        connection.execute(
            """
            UPDATE contact_entities SET
                full_name = ?,
                first_name = ?,
                last_name = ?,
                company = ?,
                company_normalized = ?,
                job_title = ?,
                department = ?,
                website = ?,
                linkedin = ?,
                address = ?,
                city = ?,
                province = ?,
                postal_code = ?,
                country = ?,
                notes = ?,
                extraction_method = 'manual_edit',
                extraction_version = ?,
                annotation_status = 'human_corrected',
                reviewed_at = ?,
                confidence = ?,
                warnings_json = ?,
                visible = 1
            WHERE contact_id = ?
            """,
            (
                full_name,
                first_name,
                last_name,
                company,
                normalize_text(company) or None,
                job_title,
                department,
                website,
                linkedin,
                address,
                city,
                province,
                postal_code,
                country,
                notes,
                extraction_version,
                utc_now_iso(),
                confidence,
                json.dumps(warnings or [], ensure_ascii=True),
                contact_id,
            ),
        )
        connection.execute("DELETE FROM contact_methods WHERE contact_id = ?", (contact_id,))
        _persist_contact_methods(connection, contact_id, existing.document_id, contact_methods)
        connection.commit()
    updated = load_contact_by_id(db_path, contact_id)
    if updated is None:
        raise ValueError(f"Contact not found after update for contact_id={contact_id}")
    return updated


def soft_delete_contact(db_path: Path, contact_id: int) -> None:
    with connect_db(db_path) as connection:
        result = connection.execute(
            "UPDATE contact_entities SET visible = 0, deleted_at = ? WHERE contact_id = ?",
            (utc_now_iso(), contact_id),
        )
        if result.rowcount == 0:
            raise ValueError(f"Contact not found for contact_id={contact_id}")
        connection.commit()


def _load_methods_by_contact(connection: sqlite3.Connection, contact_ids: list[int]) -> dict[int, list[ContactMethod]]:
    if not contact_ids:
        return {}
    placeholders = ",".join("?" for _ in contact_ids)
    rows = connection.execute(
        f"""
        SELECT *
        FROM contact_methods
        WHERE contact_id IN ({placeholders})
        ORDER BY is_primary DESC, method_id
        """,
        contact_ids,
    ).fetchall()
    methods: dict[int, list[ContactMethod]] = {}
    for row in rows:
        methods.setdefault(row["contact_id"], []).append(
            ContactMethod(
                method_type=row["method_type"],
                label=row["label"],
                raw_value=row["raw_value"],
                normalized_value=row["normalized_value"],
                is_primary=bool(row["is_primary"]),
            )
        )
    return methods


def _contact_from_row(row: sqlite3.Row, methods: list[ContactMethod]) -> ContactEntities:
    return ContactEntities(
        contact_id=row["contact_id"],
        document_id=row["document_id"],
        source_file=row["source_file"],
        contact_index=row["contact_index"],
        full_name=row["full_name"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        company=row["company"],
        job_title=row["job_title"],
        department=row["department"],
        website=row["website"],
        linkedin=row["linkedin"],
        address=row["address"],
        city=row["city"],
        province=row["province"],
        postal_code=row["postal_code"],
        country=row["country"],
        notes=row["notes"],
        contact_methods=methods,
        extraction_method=row["extraction_method"],
        confidence=row["confidence"],
        warnings=json.loads(row["warnings_json"] or "[]"),
    )


def _contact_to_api(contact: ContactEntities) -> dict[str, Any]:
    return contact.model_dump(mode="json")


def annotation_status_from_method(extraction_method: str | None) -> str:
    if not extraction_method:
        return "system_extracted"
    method = extraction_method.lower()
    if method == "manual_edit":
        return "human_corrected"
    if method.startswith("llm"):
        return "auto_annotated"
    return "system_extracted"


def average_page_confidence(raw_response: dict) -> float | None:
    pages = raw_response.get("pages") or []
    scores = [
        (page.get("confidence_scores") or {}).get("average_page_confidence_score")
        for page in pages
    ]
    numeric_scores = [score for score in scores if isinstance(score, (int, float))]
    if not numeric_scores:
        return None
    return sum(numeric_scores) / len(numeric_scores)
