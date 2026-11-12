# Insightdesk-AI

Dashboard de ventas con React + Vite, FastAPI, SQLite, Recharts y chat Gemini. Incluye vendedores, inventario, auditoría y solicitudes de aprobación para operaciones financieras sensibles.

## Configuración local

1. Copia `.env.example` como `.env` en la raíz del proyecto.
2. Configura una contraseña fuerte en `MANAGER_PASSWORD` y un secreto distinto en `APP_AUTH_SECRET`.
3. Para el chat, agrega `GEMINI_API_KEY`. Para conversiones oficiales, configura `BCCR_API_TOKEN` con el token del servicio SDDE del BCCR. No compartas estos valores por GitHub ni por el chat.
4. Inicia con `start_dashboard.ps1` o usa las instrucciones manuales siguientes.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API: `http://127.0.0.1:8000`; documentación: `/docs`. El backend carga el `.env` de la raíz sin una dependencia extra. El servidor escucha en loopback para que las aprobaciones solo estén disponibles en la computadora local.

## Frontend

En otra terminal:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Dashboard: `http://localhost:5173`.

## Primer uso

- Si `DEMO_SELLER_PASSWORD` esta configurada, el primer arranque crea seis cuentas demo (Ana Rodriguez, Luis Morales, Maria Fernanda Soto, Carlos Jimenez, Sofia Vargas y Diego Ramirez), seis ventas de muestra y movimientos demo de inventario. Son datos ficticios e idempotentes; no representan personal ni actividad real.
- Las cuentas demo comparten la contrasena local configurada en `DEMO_SELLER_PASSWORD`. Para cuentas reales, usa credenciales individuales.
- Las 50 ventas del seed original permanecen como "Sin asignar"; no se adjudican ventas historicas a vendedores ficticios.

- Inicia sesión como **Jose Castro** con `MANAGER_PASSWORD`.
- Agrega los vendedores reales y sus contraseñas individuales.
- Asigna las ventas seed a los vendedores reales en el apartado Ventas. Al inicio se muestran como “Sin asignar”.
- Registra las existencias reales mediante una solicitud de entrada y apruébala desde Aprobaciones.
- Vendedores registran las ventas; inventario insuficiente se rechaza.
- Precios, devoluciones, notas de crédito, moneda extranjera y entradas de inventario necesitan aprobación de gerencia. Los empleados y observadores pueden consultar solicitudes y el registro de acciones.
- Para pagos USD/EUR se consulta la tasa BCCR con fecha de la venta; USD usa compra CRC/USD y EUR usa EUR/USD × CRC/USD. Si falta el token oficial, la conversión se rechaza de forma explícita.

## Verificación

Desde `backend`, ejecuta:

```powershell
python -m pytest -q
python -m compileall -q app tests
```

Desde `frontend`, ejecuta `npm run build`.

## Git

`.gitignore` excluye `.env`, SQLite, logs, `node_modules`, entornos virtuales y archivos de build. Los commits se organizan en el historial de la rama; GitHub no coloca commits dentro de carpetas. Los archivos de proyecto y documentación sí se guardan en sus carpetas normales.
