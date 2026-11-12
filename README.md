# Insightdesk-AI

Plataforma de indicadores de ventas. Fases 1 y 2: base React + Vite y API FastAPI con SQLite/SQLAlchemy, validación Pydantic y seed determinista.

## Backend

Desde `backend`, crea un entorno virtual e instala `requirements.txt`. Para iniciar la API:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

La API está disponible en `http://127.0.0.1:8000`; documentación interactiva en `/docs`. La primera ejecución crea SQLite y agrega el seed si aún no hay ventas.

## Frontend

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Pruebas

Desde `backend`, activa el entorno virtual y ejecuta `python -m pytest -q`.

## Activar Gemini

1. Revoca en Google AI Studio la clave que se compartió en el chat y genera una nueva.
2. Desde la raíz, copia `.env.example` como `.env` y agrega la clave nueva en `GEMINI_API_KEY`.
3. Ejecuta `start_dashboard.ps1` de nuevo para que las ventanas de FastAPI hereden la variable. El modelo rápido predeterminado es `gemini-3.5-flash-lite`; se puede cambiar con `GEMINI_MODEL`.

La aplicación no usa ni guarda la clave que se pegó en el chat. FastAPI la lee del entorno y llama al API de Gemini; React nunca recibe esa clave.

El seed guarda una marca de inicialización; si eliminas todas las ventas desde el dashboard, no volverán al reiniciar.

Para recargar `.env` en el backend, usa `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\pc\OneDrive\Desktop\Lab_LE_Claude\ai-maze\Insightdesk-AI\start_dashboard.ps1" -RestartBackend` desde la terminal del usuario. El script mantiene el frontend si el puerto 5173 ya está activo.
