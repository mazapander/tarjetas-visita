from __future__ import annotations

import json
import sys
from typing import Any

from tarjetasvisita.config import Settings
from tarjetasvisita.extraction import extract_contact_entities_rule_based
from tarjetasvisita.normalization import normalize_phone, normalize_url, split_person_name
from tarjetasvisita.schemas import ContactEntities, ContactMethod


EXTRACTION_SYSTEM_PROMPT = """You extract contact entities from business card OCR.
Return strict JSON matching this schema:
{
  "contacts": [
    {
      "full_name": string|null,
      "first_name": string|null,
      "last_name": string|null,
      "company": string|null,
      "job_title": string|null,
      "department": string|null,
      "emails": [string],
      "phones": [string],
      "mobile_phones": [string],
      "website": string|null,
      "linkedin": string|null,
      "address": string|null,
      "city": string|null,
      "province": string|null,
      "postal_code": string|null,
      "country": string|null,
      "notes": string|null,
      "confidence": number|null,
      "warnings": [string]
    }
  ]
}
Use null or [] when a value is not visible. Do not invent data."""


def extract_contact_entities_with_llm(
    ocr_text: str,
    document_id: str,
    source_file: str | None,
    settings: Settings,
) -> list[ContactEntities]:
    heuristic = extract_contact_entities_rule_based(ocr_text, document_id=document_id, source_file=source_file)
    if not settings.llm_enabled or not _requires_llm_completion(heuristic):
        return heuristic
    try:
        payload = _call_llm_json(
            [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"OCR text:\n\n{ocr_text}"},
            ],
            settings,
        )
    except Exception as exc:
        heuristic[0].warnings.append(f"LLM extraction failed, fallback applied: {type(exc).__name__}")
        return heuristic
    contacts = parse_contact_entities_payload(payload, document_id=document_id, source_file=source_file)
    return contacts or heuristic


def parse_contact_entities_payload(
    payload: str | dict[str, Any],
    document_id: str,
    source_file: str | None = None,
) -> list[ContactEntities]:
    data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    raw_contacts = data.get("contacts") if isinstance(data.get("contacts"), list) else [data]
    contacts: list[ContactEntities] = []
    for index, item in enumerate(raw_contacts):
        full_name = item.get("full_name")
        first_name = item.get("first_name")
        last_name = item.get("last_name")
        if full_name and not (first_name or last_name):
            first_name, last_name = split_person_name(full_name)
        methods: list[ContactMethod] = []
        for email_index, email in enumerate(item.get("emails") or []):
            email_text = str(email).strip().lower()
            if email_text:
                methods.append(ContactMethod(method_type="email", raw_value=email_text, normalized_value=email_text, is_primary=email_index == 0))
        for phone_index, phone in enumerate(item.get("phones") or []):
            normalized = normalize_phone(str(phone))
            if normalized:
                methods.append(ContactMethod(method_type="phone", raw_value=str(phone), normalized_value=normalized, is_primary=phone_index == 0))
        for phone_index, phone in enumerate(item.get("mobile_phones") or []):
            normalized = normalize_phone(str(phone))
            if normalized:
                methods.append(ContactMethod(method_type="mobile", raw_value=str(phone), normalized_value=normalized, is_primary=phone_index == 0))
        website = normalize_url(item.get("website") or "") if item.get("website") else None
        linkedin = normalize_url(item.get("linkedin") or "") if item.get("linkedin") else None
        if website:
            methods.append(ContactMethod(method_type="website", raw_value=website, normalized_value=website, is_primary=True))
        if linkedin:
            methods.append(ContactMethod(method_type="linkedin", raw_value=linkedin, normalized_value=linkedin, is_primary=True))
        contacts.append(
            ContactEntities(
                document_id=document_id,
                source_file=source_file,
                contact_index=index,
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                company=item.get("company"),
                job_title=item.get("job_title"),
                department=item.get("department"),
                website=website,
                linkedin=linkedin,
                address=item.get("address"),
                city=item.get("city"),
                province=item.get("province"),
                postal_code=item.get("postal_code"),
                country=item.get("country"),
                notes=item.get("notes"),
                contact_methods=methods,
                extraction_method="llm",
                confidence=item.get("confidence"),
                warnings=item.get("warnings") or [],
            )
        )
    return contacts


def _requires_llm_completion(contacts: list[ContactEntities]) -> bool:
    if not contacts:
        return True
    contact = contacts[0]
    has_contact_method = any(method.method_type in {"email", "phone", "mobile"} for method in contact.contact_methods)
    return not contact.full_name or not contact.company or not has_contact_method or (contact.confidence or 0) < 0.7


def _call_llm_json(messages: list[dict[str, str]], settings: Settings) -> str:
    provider = settings.llm_provider.lower()
    if provider == "mistral":
        return _call_mistral_json(messages, settings)
    if provider == "openai_compatible":
        return _call_openai_compatible_json(messages, settings)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def _call_mistral_json(messages: list[dict[str, str]], settings: Settings) -> str:
    try:
        from mistralai.client import Mistral
    except ImportError as exc:
        raise RuntimeError(
            "Install mistralai in the active interpreter. "
            f"Current python: {sys.executable}"
        ) from exc
    if not settings.llm_api_key or not settings.llm_model:
        raise ValueError("LLM_API_KEY and LLM_MODEL are required for LLM_PROVIDER=mistral")
    client = Mistral(api_key=settings.llm_api_key)
    response = client.chat.complete(
        model=settings.llm_model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _call_openai_compatible_json(messages: list[dict[str, str]], settings: Settings) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Install openai in the active interpreter. "
            f"Current python: {sys.executable}"
        ) from exc
    if not settings.llm_api_key or not settings.llm_model:
        raise ValueError("LLM_API_KEY and LLM_MODEL are required for LLM_PROVIDER=openai_compatible")
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or "{}"
