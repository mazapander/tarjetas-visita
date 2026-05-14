# ExtraccionTarjetasVisitas

Aplicacion local para extraer entidades de tarjetas de visita escaneadas.

El objetivo del proyecto es convertir escaneos de tarjetas en contactos estructurados, revisables y exportables para Outlook, manteniendo separados el codigo y los documentos operativos.

## Scope Actual

La version actual es local-first:

- Procesa documentos desde `project_files/raw/cards/`.
- Ejecuta OCR con Mistral si `MISTRAL_API_KEY` esta configurada.
- Permite procesar `.txt` como entrada de prueba sin llamar a OCR externo.
- Extrae entidades de contacto con reglas heuristicas.
- Puede usar LLM como fallback si se configura proveedor compatible.
- Guarda documentos, OCR y contactos en SQLite.
- Exporta contactos a CSV compatible con Outlook y a VCF.
- Sirve una UI React + TypeScript compilada con Vite desde FastAPI.

No incluye todavia:

- Sincronizacion directa con Outlook/Microsoft Graph.
- Autenticacion de usuarios.
- Docker Compose.
- Panel avanzado de correccion.
- Separacion automatica robusta de multiples tarjetas dentro de una misma imagen.

## Estructura

```text
.
├── .venv/                         # entorno Python local, no versionado
├── .env                           # variables locales, no versionado
├── .env.example                   # plantilla de configuracion
├── AGENTS.md                      # reglas operativas para agentes
├── framework/                     # metodologia, agentes, skills y docs vivas
├── code/
│   ├── pyproject.toml             # paquete Python instalable
│   ├── src/tarjetasvisita/        # backend, pipeline, OCR, SQLite, exports
│   ├── tests/                     # tests backend
│   └── web/                       # frontend React + TypeScript
└── project_files/
    ├── raw/cards/                 # escaneos o .txt de entrada
    ├── processed/ocr/             # OCR generado/cacheado
    ├── processed/entities/        # entidades generadas
    ├── app/tarjetasvisita.db      # SQLite local
    ├── exports/                   # outlook.csv y contacts.vcf
    └── reports/                   # salidas de analisis futuras
```

`project_files/` contiene datos personales y salidas generadas. Esta protegido por `.gitignore` salvo los `.gitkeep` necesarios.

## Ejecutar En Local

Desde la raiz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".\code[dev]"
Copy-Item .env.example .env
```

Opcionalmente edita `.env` y configura:

```env
MISTRAL_API_KEY=
LLM_PROVIDER=disabled
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
```

Para compilar la UI:

```powershell
cd code\web
npm install
npm run build
cd ..\..
```

Para desarrollar la UI con hot reload:

```powershell
cd code\web
npm install
npm run dev
```

Para arrancar la aplicacion:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn tarjetasvisita.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Abre:

```text
http://127.0.0.1:8000
```

## Flujo De Uso

1. Copia escaneos a:
   ```text
   project_files/raw/cards/
   ```
2. Si son imagenes/PDF reales, configura `MISTRAL_API_KEY` en `.env`.
3. Si solo quieres probar el pipeline sin OCR externo, crea un `.txt` en `project_files/raw/cards/` con el texto de una tarjeta.
4. Pulsa `Procesar` en la UI o llama al endpoint:
   ```powershell
   Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/pipeline/process -ContentType "application/json" -Body '{"mode":"new_or_changed"}'
   ```
5. Revisa contactos en la UI.
6. Haz click sobre un nombre para abrir la tarjeta, editar campos y reutilizar entidades detectadas por el OCR.
7. Selecciona los registros que quieras exportar y descarga solo esa seleccion en CSV o VCF.
8. Descarga exports:
   ```text
   http://127.0.0.1:8000/api/exports/outlook.csv
   http://127.0.0.1:8000/api/exports/contacts.vcf
   ```

## API Principal

```text
GET  /api/health
GET  /api/dashboard/summary
GET  /api/contacts
GET  /api/contacts/{contact_id}
PATCH /api/contacts/{contact_id}
POST /api/contacts/{contact_id}/delete
POST /api/pipeline/process
POST /api/pipeline/upload
POST /api/pipeline/reextract/{document_id}
GET  /api/files/documents/{document_id}
GET  /api/exports/outlook.csv
GET  /api/exports/contacts.vcf
```

## Verificacion

Backend:

```powershell
cd code
..\.venv\Scripts\python -m pytest
```

Si PowerShell interpreta mal la ruta anterior, usa:

```powershell
cd code
..\.venv\Scripts\python.exe -m pytest
```

O desde la raiz:

```powershell
.\.venv\Scripts\python -m pytest code
```

Frontend:

```powershell
cd code\web
npm install
npm run build
```

## Datos Y Seguridad

No versionar:

- `.env`
- `project_files/raw/**`
- `project_files/processed/**`
- `project_files/app/**`
- `project_files/exports/**`
- `project_files/reports/**`
- imagenes, PDFs, DBs, CSVs y VCFs generados

Si hacen falta fixtures para tests, deben ser anonimos y vivir dentro de `code/tests/`.

## Metodologia De Trabajo

La metodologia vive en `framework/`:

- `framework/docs/AI_DEV_OPERATING_SYSTEM.md`
- `framework/docs/token-optimization.md`
- `framework/docs/project-status.md`
- `framework/agents/`
- `framework/skills/`

Para trabajar con IA en este repo:

1. Usar el menor contexto posible.
2. Preferir `rg --files`, archivos concretos y diffs.
3. Evitar meter `project_files/` en contexto.
4. Antes de codificar, devolver analisis, supuestos, riesgos, plan minimo y criterios.
5. Despues de cambios, actualizar `framework/docs/project-status.md` si cambia el estado del proyecto.
