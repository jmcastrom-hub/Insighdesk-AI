# Backend Insightdesk-AI

FastAPI + SQLite/SQLAlchemy. Inicia con:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

El backend lee `.env` desde la raíz del proyecto. Define `MANAGER_PASSWORD` y `APP_AUTH_SECRET` para sesiones; define `BCCR_API_TOKEN` para las tasas oficiales y `GEMINI_API_KEY` para el chat. La API de aprobación solo acepta solicitudes de gerente desde loopback.

La creación del esquema agrega campos compatibles a SQLite existente. Existencias nuevas inician en cero; las 50 ventas seed no se asignan a vendedores automáticamente.

Pruebas: `python -m pytest -q`.
