# ExtraccionTarjetasVisitas

App local-first para procesar escaneos de tarjetas de visita, extraer entidades de contacto, revisar resultados y exportar contactos para Outlook.

## Setup

```powershell
python -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item ..\.env.example ..\.env
```

## Flujo local

1. Copia escaneos a `..\project_files\raw\cards\`.
2. Configura `MISTRAL_API_KEY` en `..\.env` si quieres OCR real.
3. Ejecuta:

```powershell
python -m uvicorn tarjetasvisita.api.app:app --reload
```

4. En otra terminal, para trabajar la UI con Vite:

```powershell
cd web
npm install
npm run dev
```

5. Abre `http://127.0.0.1:5173` en desarrollo o `http://127.0.0.1:8000` si has hecho `npm run build`.

SQLite, OCR, entidades, exports y reports se guardan en `..\project_files\`.
