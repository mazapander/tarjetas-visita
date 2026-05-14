# Project Status

Documento vivo para entender rapidamente el estado de `ExtraccionTarjetasVisitas`.

Ultima actualizacion: 2026-05-14

## Resumen

El proyecto es una app local-first para extraer entidades de tarjetas de visita escaneadas y exportarlas como contactos importables en Outlook.

La arquitectura actual separa:

- `code/`: aplicacion, backend, frontend y tests.
- `project_files/`: documentos, OCR, SQLite, exports y reports.
- `framework/`: metodologia de trabajo, agentes, skills, prompts y documentacion viva.

## Estado Actual

Implementado:

- Entorno Python local en `.venv/`.
- Backend instalable desde `code/`.
- FastAPI con endpoints de salud, contactos, pipeline, archivos y exports.
- SQLite local en `project_files/app/tarjetasvisita.db`.
- Pipeline incremental desde `project_files/raw/cards/`.
- OCR Mistral opcional si existe `MISTRAL_API_KEY`.
- Entrada `.txt` para pruebas sin OCR externo.
- Extraccion heuristica de nombre, empresa, cargo, email, telefono, web y direccion basica.
- Fallback LLM opcional con proveedor `mistral` u `openai_compatible`.
- Exports `project_files/exports/outlook.csv` y `project_files/exports/contacts.vcf`.
- UI React + TypeScript compilable en `code/web/dist`.
- Visualizacion de tarjeta escaneada al abrir un contacto.
- Edicion manual de datos desde la UI.
- Soft delete por contacto usando `visible = 0`.
- Export CSV/VCF de seleccion visible desde la lista.
- Asistente OCR para importar entidades detectadas al formulario.
- Tests backend basicos.
- `.gitignore` orientado a proteger datos personales y outputs generados.

Pendiente:

- Mejorar separacion de multiples tarjetas dentro de una misma imagen.
- Mejorar normalizacion de telefonos internacionales y direcciones.
- Gestion visual de subida de archivos desde la UI.
- Benchmark/evaluacion con tarjetas anonimizadas.
- Sincronizacion directa con Outlook via Microsoft Graph, fuera de v1.
- Docker Compose, fuera del scope inicial.

## Decisiones Del Proyecto

### 001 - Local-first con SQLite

Se usa SQLite como fuente local de verdad para evitar infraestructura innecesaria en v1.

Motivo:

- Volumen esperado bajo/medio.
- Uso local.
- Backup sencillo.
- Consultas suficientes para revision y export.

### 002 - Separacion `code/` y `project_files/`

El codigo vive en `code/` y los datos operativos viven en `project_files/`.

Motivo:

- Evita mezclar datos personales con codigo.
- Facilita ignorar outputs por Git.
- Hace mas claro que se puede borrar/regenerar parte del estado operativo.

### 003 - OCR externo opcional

Mistral OCR se usa solo si `MISTRAL_API_KEY` esta configurada.

Motivo:

- Permite pruebas locales con `.txt`.
- Evita bloquear desarrollo por API externa.
- Mantiene compatibilidad con el patron usado en FACTURASOCR.

### 004 - Outlook por export en v1

La integracion inicial con Outlook es CSV/VCF, no Microsoft Graph.

Motivo:

- Menor complejidad.
- Sin OAuth ni permisos corporativos en v1.
- SQLite sigue siendo fuente de verdad.

### 005 - Framework como guia operativa

La documentacion metodologica vive en `framework/`.

Motivo:

- Separa la app real del sistema de trabajo.
- Permite a agentes usar roles, skills y reglas sin contaminar el scope del producto.

### 006 - Frontend React componentizado

La web deja de ser un script plano y pasa a React + TypeScript + Vite con componentes reutilizables.

Motivo:

- Escala mejor para vistas y flujos mas ricos.
- Facilita reutilizar tabla, paneles y asistentes en futuros proyectos.
- Mejora mantenibilidad de interacciones complejas como seleccion, preview, OCR assist y edicion manual.

## Features

| Feature | Estado | Notas |
|---|---|---|
| Scaffold `code/` + `project_files/` | Hecho | Separacion de codigo y datos operativos. |
| Backend FastAPI | Hecho | API local con endpoints principales. |
| SQLite local | Hecho | Bootstrap simple sin migraciones. |
| OCR Mistral opcional | Hecho | Requiere `MISTRAL_API_KEY`. |
| Procesamiento `.txt` | Hecho | Util para pruebas sin OCR. |
| Extraccion heuristica | Hecho | Campos basicos de contacto. |
| Fallback LLM | Basico | Configurable por `.env`. |
| UI React componentizada | Hecho | Tabla, resumen, detalle, OCR assist y procesado. |
| Vista previa de tarjeta | Hecho | Imagen/PDF visible desde el panel derecho. |
| Edicion manual | Hecho | PATCH desde UI sobre el contacto activo. |
| Soft delete | Hecho | Oculta el contacto con `visible = 0`. |
| Export por seleccion | Hecho | CSV/VCF usando contactos marcados en la lista. |
| Export Outlook CSV | Hecho | `project_files/exports/outlook.csv`. |
| Export VCF | Hecho | `project_files/exports/contacts.vcf`. |
| Outlook Graph directo | Fuera de v1 | Requiere decision de auth/permisos. |

## Branches Y Cambios

Estado Git local:

- `master` y `web` estaban alineadas antes de empezar el refactor del frontend.
- El refactor actual se ha desarrollado en la rama `web`.

Registro actual:

```text
branch: web
objetivo: refactorizar la web a React componentizado con edicion, preview, OCR assist y export por seleccion
cambios: Vite + React + TypeScript, componentes reutilizables, asistente OCR en formulario, tabla operativa mas rica
verificacion: npm install, npm run build, pytest
riesgos: faltan tests de frontend y subida visual de archivos
```

Formato recomendado:

```text
branch: feature/nombre-corto
objetivo:
cambios:
verificacion:
riesgos:
```

## Verificacion Conocida

Ultima verificacion ejecutada:

```powershell
.\.venv\Scripts\python -m pip install -e ".\code[dev]"
cd code
..\.venv\Scripts\python -m pytest
cd web
npm run build
```

Resultado conocido:

- Tests backend: 3 passed.
- Tests backend: 4 passed.
- Build frontend: correcto.
- Prueba manual: procesado de tarjeta `.txt` desde `project_files/raw/cards/`.

## Guia Rapida Para Nuevos Cambios

Antes de pedir o hacer cambios:

1. Leer `AGENTS.md`.
2. Usar `framework/docs/AI_DEV_OPERATING_SYSTEM.md`.
3. Aplicar `framework/docs/token-optimization.md`.
4. Consultar este documento para estado y decisiones.
5. Limitar contexto a:
   - issue o peticion actual,
   - `README.md`,
   - `framework/docs/project-status.md`,
   - archivos concretos bajo `code/` que vayan a tocarse.

No incluir `project_files/` en contexto salvo que se trate de un fixture anonimo o una prueba manual local.

## Proximos Pasos Recomendados

1. Crear fixtures anonimos en `code/tests/fixtures/`.
2. Mejorar heuristicas con 5-10 tarjetas reales anonimizadas.
3. Añadir subida visual de archivos a la UI React.
4. Anadir evaluacion de calidad: campos detectados, campos faltantes, confianza media.
5. Decidir si Outlook Graph entra en v2 o se mantiene solo export.
