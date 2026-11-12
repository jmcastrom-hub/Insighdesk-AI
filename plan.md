# Plan de Ejecución

- [x] **Fase 1: Inicialización y Estructura**
  - Crear estructura React + Vite (Frontend).
  - Crear estructura FastAPI con endpoint `/health` (Backend).
  - Generar `package.json` y `requirements.txt`.
  - Configurar `README.md` e inicializar repositorio Git.

- [x] **Fase 2: Base de Datos, Modelos y API Core**
  - Configurar SQLite y SQLAlchemy.
  - Crear entidades `Producto` y `Venta`.
  - Implementar seed reproducible de 50 ventas.
  - Crear endpoints REST y calcular indicadores.
  - Implementar validaciones Pydantic y pruebas con pytest.
  - Decisión aprobada: `/indicadores` agrega todas las ventas persistidas, incluido el seed.
  - Evidencia/verificación: `backend/app/database.py`, `models.py`, `schemas.py`, `seed.py`, `routers.py`; pruebas **6 passed**.

- [x] **Fase 3: Dashboard Frontend**
  - Conectar React con FastAPI mediante `GET /indicadores`.
  - Implementar gráficos Recharts y tres KPI.
  - Corregir CORS para los orígenes locales de Vite.
  - Evidencia/verificación: `frontend/src/main.jsx`, `styles.css`; `npm run build` correcto; captura real de Chrome con datos del seed.

- [ ] **Fase 4: Agente IA y gestión funcional**
  - Agregar CRUD de productos y ventas (`PATCH`, `DELETE`) con validaciones, recálculo del total de venta y protección del historial relacionado.
  - Crear chat React conectado a `POST /chat`.
  - Integrar Gemini por REST del lado de FastAPI; clave en `GEMINI_API_KEY`, modelo configurable y límites de contexto/salida.
  - Construir el contexto del agente desde indicadores, catálogo y hasta 50 ventas recientes; la clave no se expone al navegador.
  - Añadir estados de carga/error, validación de mensajes y respuesta clara si falta la clave.
  - Hacer que eliminar todas las ventas persista tras reiniciar, mediante una marca interna del seed.
  - Evidencia: `backend/app/agent.py`, `routers.py`, `schemas.py`, `models.py`, `seed.py`; `frontend/src/Management.jsx`, `ChatWidget.jsx`, `management.css`; `.env.example`, `start_dashboard.ps1`.
  - Verificación: pytest **6 passed**; `compileall` correcto; `npm run build` correcto; smoke REST en SQLite temporal verificó GET/POST/PATCH/DELETE y chat sin clave (503 controlado).
  - Configuración local: clave en `.env` (ignorado por Git); el backend requiere reinicio para tomarla.
  - Estado pendiente: una petición real al chat terminó en timeout. El test TCP 443 del equipo del usuario fue exitoso, pero falta confirmar una respuesta real de Gemini. Ver `docs/bitacora-validacion.md`.
