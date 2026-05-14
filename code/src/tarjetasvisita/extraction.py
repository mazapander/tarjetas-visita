from __future__ import annotations

import re

from tarjetasvisita.normalization import (
    dedupe_preserve_order,
    extract_emails,
    extract_phone_numbers,
    extract_urls,
    normalize_text,
    split_person_name,
)
from tarjetasvisita.schemas import ContactEntities, ContactMethod


COMPANY_TOKENS = {
    "s.l.",
    "sl",
    "s.a.",
    "sa",
    "inc",
    "llc",
    "ltd",
    "gmbh",
    "group",
    "grupo",
    "solutions",
    "consulting",
    "technologies",
    "ingenieria",
}
TITLE_TOKENS = {
    "director",
    "manager",
    "sales",
    "ventas",
    "gerente",
    "ceo",
    "cto",
    "cfo",
    "responsable",
    "consultor",
    "account",
    "business",
    "marketing",
    "engineer",
    "ingeniero",
}
ADDRESS_TOKENS = {"calle", "c/", "avenida", "avda", "plaza", "poligono", "paseo", "street", "road"}


def extract_contact_entities_rule_based(
    ocr_text: str,
    document_id: str,
    source_file: str | None = None,
) -> list[ContactEntities]:
    lines = _clean_lines(ocr_text)
    emails = extract_emails(ocr_text)
    phones = extract_phone_numbers(ocr_text)
    urls = extract_urls(ocr_text)
    linkedin = next((url for url in urls if "linkedin." in url.lower()), None)
    website = next((url for url in urls if "linkedin." not in url.lower()), None)

    full_name = _extract_person_name(lines)
    first_name, last_name = split_person_name(full_name)
    company = _extract_company(lines, full_name)
    job_title = _extract_job_title(lines)
    address = _extract_address(lines)
    postal_code, city = _extract_postal_city(lines)

    methods: list[ContactMethod] = []
    for index, email in enumerate(emails):
        methods.append(ContactMethod(method_type="email", raw_value=email, normalized_value=email, is_primary=index == 0))
    for index, phone in enumerate(phones):
        method_type = "mobile" if _looks_mobile(phone) else "phone"
        methods.append(ContactMethod(method_type=method_type, raw_value=phone, normalized_value=phone, is_primary=index == 0))
    if website:
        methods.append(ContactMethod(method_type="website", raw_value=website, normalized_value=website, is_primary=True))
    if linkedin:
        methods.append(ContactMethod(method_type="linkedin", raw_value=linkedin, normalized_value=linkedin, is_primary=True))

    warnings = ["Heuristic extraction used."]
    if not full_name:
        warnings.append("Contact name not found confidently.")
    if not company:
        warnings.append("Company not found confidently.")
    if not emails and not phones:
        warnings.append("No email or phone found.")

    contact = ContactEntities(
        document_id=document_id,
        source_file=source_file,
        contact_index=0,
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        company=company,
        job_title=job_title,
        website=website,
        linkedin=linkedin,
        address=address,
        city=city,
        postal_code=postal_code,
        contact_methods=methods,
        extraction_method="heuristic",
        confidence=_estimate_confidence(full_name, company, emails, phones, website),
        warnings=warnings,
    )
    return [contact]


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().strip("|").strip()
        if not line or line.startswith("![") or line.startswith("[tbl-"):
            continue
        line = re.sub(r"\s+", " ", line.lstrip("#").strip())
        if line:
            lines.append(line)
    return lines


def _is_noise_line(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized:
        return True
    if "@" in line or "http" in normalized or "www." in normalized:
        return True
    if re.search(r"\d{5,}", line):
        return True
    if any(token in normalized for token in ADDRESS_TOKENS):
        return True
    return False


def _extract_person_name(lines: list[str]) -> str | None:
    candidates: list[tuple[int, str]] = []
    for line in lines[:12]:
        if _is_noise_line(line):
            continue
        normalized = normalize_text(line)
        words = [word for word in re.split(r"\s+", line) if word]
        if not 2 <= len(words) <= 5:
            continue
        if any(token in normalized for token in COMPANY_TOKENS | TITLE_TOKENS):
            continue
        if not any(char.isupper() for char in line):
            continue
        score = 10
        if line == line.upper():
            score -= 2
        if any(word[:1].isupper() for word in words):
            score += 4
        candidates.append((score, line.strip(" -*:")))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def _extract_company(lines: list[str], full_name: str | None) -> str | None:
    candidates: list[tuple[int, str]] = []
    for line in lines[:14]:
        if _is_noise_line(line):
            continue
        if full_name and normalize_text(line) == normalize_text(full_name):
            continue
        normalized = normalize_text(line)
        score = 0
        if any(token in normalized for token in COMPANY_TOKENS):
            score += 20
        if line == line.upper() and len(line) > 3:
            score += 6
        if len(line.split()) <= 5:
            score += 2
        if any(token in normalized for token in TITLE_TOKENS):
            score -= 10
        if score > 0:
            candidates.append((score, line.strip(" -*:")))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def _extract_job_title(lines: list[str]) -> str | None:
    for line in lines:
        normalized = normalize_text(line)
        if any(token in normalized for token in TITLE_TOKENS):
            return line.strip(" -*:")
    return None


def _extract_address(lines: list[str]) -> str | None:
    for line in lines:
        normalized = normalize_text(line)
        if any(token in normalized for token in ADDRESS_TOKENS):
            return line.strip()
    return None


def _extract_postal_city(lines: list[str]) -> tuple[str | None, str | None]:
    for line in lines:
        match = re.search(r"\b(\d{5})\b\s*[-,]?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ .-]{2,})?", line)
        if match:
            city = match.group(2).strip(" ,.-") if match.group(2) else None
            return match.group(1), city
    return None, None


def _looks_mobile(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return digits.startswith(("6", "7")) or digits.startswith(("346", "347"))


def _estimate_confidence(
    full_name: str | None,
    company: str | None,
    emails: list[str],
    phones: list[str],
    website: str | None,
) -> float:
    score = 0.2
    if full_name:
        score += 0.25
    if company:
        score += 0.2
    if emails:
        score += 0.2
    if phones:
        score += 0.1
    if website:
        score += 0.05
    return round(min(score, 0.95), 2)


def normalized_contact_keys(contact: ContactEntities) -> list[str]:
    keys = [method.normalized_value for method in contact.contact_methods if method.method_type in {"email", "phone", "mobile"}]
    return dedupe_preserve_order(keys)
