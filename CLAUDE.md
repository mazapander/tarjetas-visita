# CLAUDE.md

PWA para escanear tarjetas de visita, extraer contactos con OCR y exportarlos.
Las reglas generales de trabajo están en @AGENTS.md.

## Mapa

- `code/src/tarjetasvisita/`: backend FastAPI (`api/app.py`), pipeline, OCR (Mistral), extracción, SQLite.
- `code/web/src/`: frontend React + TypeScript (Vite).
- `code/tests/`: tests backend y `fixtures/` sintéticas.
- `project_files/`: datos personales y salidas. No leer nunca.

## Comandos

```bash
pip install -e "./code[dev]"
pytest code                          # tests backend
python code/scripts/eval_extraction.py   # calidad de extracción
cd code/web && npm ci && npm run build   # tsc + build
uvicorn tarjetasvisita.api.app:app --reload
```

## Ahorro de tokens

- El plugin `ponytail` está activo en este repo (`.claude/settings.json`): escribe el mínimo código que funcione. `/ponytail lite` si una tarea necesita más andamiaje.
- Busca con `rg`/Glob antes de leer; lee rangos de líneas, no ficheros enteros.
- No leas `package-lock.json`, `dist/`, `node_modules/` ni `project_files/` (bloqueados por permisos).
- La metodología extensa vive en `docs/internal/`: ábrela solo si la tarea la pide.
- Respuestas cortas: diff + verificación, sin repetir código ya mostrado.
