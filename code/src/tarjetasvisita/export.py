from __future__ import annotations

import csv
from pathlib import Path

from tarjetasvisita.schemas import ContactEntities


def _primary(contact: ContactEntities, method_type: str) -> str | None:
    methods = [method for method in contact.contact_methods if method.method_type == method_type]
    if not methods:
        return None
    primary = next((method for method in methods if method.is_primary), methods[0])
    return primary.normalized_value


def _all_values(contact: ContactEntities, method_type: str) -> list[str]:
    return [method.normalized_value for method in contact.contact_methods if method.method_type == method_type]


def selected_contacts(contacts: list[ContactEntities], contact_ids: list[int] | None = None) -> list[ContactEntities]:
    if not contact_ids:
        return contacts
    selected_ids = set(contact_ids)
    return [contact for contact in contacts if contact.contact_id in selected_ids]


def write_outlook_csv(
    contacts: list[ContactEntities],
    csv_path: Path,
    contact_ids: list[int] | None = None,
) -> Path:
    contacts = selected_contacts(contacts, contact_ids)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "First Name",
        "Last Name",
        "Name",
        "Company",
        "Job Title",
        "E-mail Address",
        "E-mail 2 Address",
        "Mobile Phone",
        "Business Phone",
        "Business Fax",
        "Web Page",
        "Business Street",
        "Business City",
        "Business State",
        "Business Postal Code",
        "Business Country/Region",
        "Notes",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for contact in contacts:
            emails = _all_values(contact, "email")
            phones = _all_values(contact, "phone")
            mobiles = _all_values(contact, "mobile")
            writer.writerow(
                {
                    "First Name": contact.first_name or "",
                    "Last Name": contact.last_name or "",
                    "Name": contact.full_name or "",
                    "Company": contact.company or "",
                    "Job Title": contact.job_title or "",
                    "E-mail Address": emails[0] if emails else "",
                    "E-mail 2 Address": emails[1] if len(emails) > 1 else "",
                    "Mobile Phone": mobiles[0] if mobiles else "",
                    "Business Phone": phones[0] if phones else "",
                    "Business Fax": _primary(contact, "fax") or "",
                    "Web Page": contact.website or _primary(contact, "website") or "",
                    "Business Street": contact.address or "",
                    "Business City": contact.city or "",
                    "Business State": contact.province or "",
                    "Business Postal Code": contact.postal_code or "",
                    "Business Country/Region": contact.country or "",
                    "Notes": contact.notes or "",
                }
            )
    return csv_path


def write_vcf(
    contacts: list[ContactEntities],
    vcf_path: Path,
    contact_ids: list[int] | None = None,
) -> Path:
    contacts = selected_contacts(contacts, contact_ids)
    vcf_path.parent.mkdir(parents=True, exist_ok=True)
    cards: list[str] = []
    for contact in contacts:
        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(f"N:{contact.last_name or ''};{contact.first_name or ''};;;")
        lines.append(f"FN:{contact.full_name or contact.company or 'Contacto'}")
        if contact.company:
            lines.append(f"ORG:{contact.company}")
        if contact.job_title:
            lines.append(f"TITLE:{contact.job_title}")
        for method in contact.contact_methods:
            if method.method_type == "email":
                lines.append(f"EMAIL;TYPE=INTERNET:{method.normalized_value}")
            elif method.method_type == "mobile":
                lines.append(f"TEL;TYPE=CELL:{method.normalized_value}")
            elif method.method_type == "phone":
                lines.append(f"TEL;TYPE=WORK:{method.normalized_value}")
            elif method.method_type in {"website", "linkedin"}:
                lines.append(f"URL:{method.normalized_value}")
        if contact.address:
            lines.append(f"ADR;TYPE=WORK:;;{contact.address};{contact.city or ''};{contact.province or ''};{contact.postal_code or ''};{contact.country or ''}")
        if contact.notes:
            lines.append(f"NOTE:{contact.notes}")
        lines.append("END:VCARD")
        cards.append("\n".join(lines))
    vcf_path.write_text("\n\n".join(cards), encoding="utf-8")
    return vcf_path
