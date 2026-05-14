from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
from typing import Any

from tarjetasvisita.schemas import OcrResult


MISTRAL_OCR_MODEL = "mistral-ocr-latest"


def _mime_type(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".heif": "image/heif",
    }.get(path.suffix.lower(), "application/octet-stream")


def _to_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{_mime_type(path)};base64,{encoded}"


def _response_to_dict(response: Any) -> dict:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    if isinstance(response, dict):
        return response
    return json.loads(json.dumps(response, default=str))


def extract_markdown(raw_response: dict) -> str:
    pages = raw_response.get("pages") or []
    chunks: list[str] = []
    for page in pages:
        markdown = page.get("markdown") or page.get("text") or ""
        if markdown:
            chunks.append(markdown)
    return "\n\n".join(chunks).strip()


def run_mistral_ocr(document_path: Path, document_id: str, api_key: str) -> OcrResult:
    try:
        from mistralai.client import Mistral
    except ImportError as exc:
        raise RuntimeError(
            "Install mistralai in the active interpreter. "
            f"Current python: {sys.executable}"
        ) from exc

    client = Mistral(api_key=api_key)
    if document_path.suffix.lower() == ".pdf":
        document = {"type": "document_url", "document_url": _to_data_url(document_path)}
    else:
        document = {"type": "image_url", "image_url": _to_data_url(document_path)}

    response = client.ocr.process(
        model=MISTRAL_OCR_MODEL,
        document=document,
        table_format="markdown",
        confidence_scores_granularity="page",
    )
    raw = _response_to_dict(response)
    return OcrResult(
        document_id=document_id,
        source_file=document_path.name,
        provider="mistral",
        model=MISTRAL_OCR_MODEL,
        text=extract_markdown(raw),
        raw_response=raw,
    )


def ocr_from_text_file(document_path: Path, document_id: str) -> OcrResult:
    text = document_path.read_text(encoding="utf-8")
    return OcrResult(
        document_id=document_id,
        source_file=document_path.name,
        provider="local_text",
        model="text-file",
        text=text,
        raw_response={"pages": [{"markdown": text}], "usage_info": {"pages_processed": 1}},
    )


def save_ocr_result(result: OcrResult, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{result.document_id}.json"
    md_path = output_dir / f"{result.document_id}.md"
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(result.text, encoding="utf-8")
    return json_path, md_path


def load_saved_ocr_results(output_dir: Path) -> list[OcrResult]:
    results: list[OcrResult] = []
    if not output_dir.exists():
        return results
    for json_path in sorted(output_dir.glob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        results.append(OcrResult.model_validate(payload))
    return results
