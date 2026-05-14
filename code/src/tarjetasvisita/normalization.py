from __future__ import annotations

import re
import unicodedata


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_RE = re.compile(r"\b(?:https?://)?(?:www\.)?[A-Z0-9.-]+\.[A-Z]{2,}(?:/[^\s]*)?\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s()./-]{6,}\d)")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = normalize_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value.strip())
    return output


def extract_emails(text: str) -> list[str]:
    return dedupe_preserve_order([match.group(0).lower() for match in EMAIL_RE.finditer(text)])


def normalize_phone(value: str) -> str:
    value = value.strip()
    prefix = "+" if value.startswith("+") else ""
    digits = re.sub(r"\D", "", value)
    return f"{prefix}{digits}" if digits else ""


def extract_phone_numbers(text: str) -> list[str]:
    phones: list[str] = []
    for match in PHONE_RE.finditer(text):
        normalized = normalize_phone(match.group(0))
        if len(re.sub(r"\D", "", normalized)) >= 7:
            phones.append(normalized)
    return dedupe_preserve_order(phones)


def normalize_url(value: str) -> str:
    cleaned = value.strip().rstrip(".,;)")
    if "@" in cleaned:
        return ""
    if not cleaned.lower().startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in URL_RE.finditer(text):
        raw = match.group(0)
        if EMAIL_RE.search(raw) or (match.start() > 0 and text[match.start() - 1] == "@"):
            continue
        normalized = normalize_url(raw)
        if normalized:
            urls.append(normalized)
    return dedupe_preserve_order(urls)


def split_person_name(full_name: str | None) -> tuple[str | None, str | None]:
    if not full_name:
        return None, None
    parts = [part for part in full_name.split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])
