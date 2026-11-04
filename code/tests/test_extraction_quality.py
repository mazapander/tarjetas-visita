import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "eval_extraction.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
spec = importlib.util.spec_from_file_location("eval_extraction", SCRIPT)
eval_extraction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_extraction)

# Suelos de calidad. Súbelos cuando mejore la extracción; no los bajes sin motivo.
# cards_synthetic: se usa para ajustar reglas. cards_holdout: NO se ajusta contra él; mide generalización.
MIN_SCORES = {
    "cards_synthetic.jsonl": {
        "full_name": 1.0, "company": 1.0, "job_title": 1.0, "email": 1.0,
        "website": 1.0, "postal_code": 1.0, "city": 1.0, "phones": 1.0,
    },
    "cards_holdout.jsonl": {
        "full_name": 0.75, "company": 0.5, "job_title": 0.375, "email": 1.0,
        "website": 1.0, "postal_code": 1.0, "city": 1.0, "phones": 1.0,
    },
}


@pytest.mark.parametrize("dataset", sorted(MIN_SCORES))
def test_extraction_quality_does_not_regress(dataset):
    scores, _ = eval_extraction.evaluate(FIXTURES / dataset)
    floors = MIN_SCORES[dataset]
    regressions = {field: (round(scores[field], 2), floor) for field, floor in floors.items() if scores[field] + 1e-9 < floor}
    assert not regressions, f"{dataset}: campos por debajo del suelo (obtenido, mínimo): {regressions}"
