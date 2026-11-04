"""Mide la precisión por campo de la extracción heurística sobre el dataset sintético.

Uso: python code/scripts/eval_extraction.py [--dataset RUTA] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR / "src"))

from tarjetasvisita.extraction import extract_contact_entities_rule_based  # noqa: E402
from tarjetasvisita.normalization import normalize_text  # noqa: E402

DEFAULT_DATASET = CODE_DIR / "tests" / "fixtures" / "cards_synthetic.jsonl"
TEXT_FIELDS = ["full_name", "company", "job_title", "email", "website", "postal_code", "city"]
FIELDS = TEXT_FIELDS + ["phones"]


def _phone_key(value: str) -> str:
    """Últimos 9 dígitos: compara sin prefijo internacional."""
    return re.sub(r"\D", "", value)[-9:]


def _predicted(contact) -> dict:
    methods = contact.contact_methods
    email = next((m.normalized_value for m in methods if m.method_type == "email"), None)
    phones = [m.normalized_value for m in methods if m.method_type in {"phone", "mobile"}]
    return {
        "full_name": contact.full_name,
        "company": contact.company,
        "job_title": contact.job_title,
        "email": email,
        "website": contact.website,
        "postal_code": contact.postal_code,
        "city": contact.city,
        "phones": phones,
    }


def _match(field: str, expected, predicted) -> bool:
    if field == "phones":
        return {_phone_key(p) for p in expected} <= {_phone_key(p) for p in predicted}
    return normalize_text(expected) == normalize_text(predicted)


def evaluate(dataset: Path = DEFAULT_DATASET) -> tuple[dict[str, float], list[dict]]:
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    hits = {field: 0 for field in FIELDS}
    failures: list[dict] = []
    for row in rows:
        contact = extract_contact_entities_rule_based(row["text"], document_id=row["id"])[0]
        predicted = _predicted(contact)
        for field in FIELDS:
            expected = row["expected"].get(field)
            if _match(field, expected, predicted[field]):
                hits[field] += 1
            else:
                failures.append({"id": row["id"], "field": field, "expected": expected, "predicted": predicted[field]})
    scores = {field: hits[field] / len(rows) for field in FIELDS}
    return scores, failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--verbose", action="store_true", help="muestra cada fallo")
    args = parser.parse_args()

    scores, failures = evaluate(args.dataset)
    print(f"{'campo':<12} precisión")
    for field, score in scores.items():
        print(f"{field:<12} {score:6.0%}")
    print(f"{'media':<12} {sum(scores.values()) / len(scores):6.0%}")
    if args.verbose:
        for failure in failures:
            print(f"- {failure['id']} {failure['field']}: esperado={failure['expected']!r} obtenido={failure['predicted']!r}")


if __name__ == "__main__":
    main()
