from __future__ import annotations

from pydantic import BaseModel, Field


class ContactMethod(BaseModel):
    method_type: str
    raw_value: str
    normalized_value: str
    label: str | None = None
    is_primary: bool = False


class ContactEntities(BaseModel):
    contact_id: int | None = None
    document_id: str
    source_file: str | None = None
    contact_index: int = 0
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
    extraction_method: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class OcrResult(BaseModel):
    document_id: str
    source_file: str
    provider: str
    model: str
    text: str
    raw_response: dict
