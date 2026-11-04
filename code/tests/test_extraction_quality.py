import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "eval_extraction.py"
spec = importlib.util.spec_from_file_location("eval_extraction", SCRIPT)
eval_extraction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_extraction)

# Suelo de calidad sobre el dataset sintético. Súbelo cuando mejore la extracción; nunca lo bajes sin motivo.
MIN_SCORES = {
    "full_name": 0.79,
    "company": 0.54,
    "job_title": 0.62,
    "email": 1.0,
    "website": 0.58,
    "postal_code": 1.0,
    "city": 1.0,
    "phones": 0.91,
}


def test_extraction_quality_does_not_regress():
    scores, _ = eval_extraction.evaluate()
    regressions = {field: (round(scores[field], 2), floor) for field, floor in MIN_SCORES.items() if scores[field] + 1e-9 < floor}
    assert not regressions, f"Campos por debajo del suelo (obtenido, mínimo): {regressions}"
