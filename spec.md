# Especificaciones Técnicas

## Stack tecnológico

- **Frontend:** React + Vite, Recharts.
- **Backend:** FastAPI, Pydantic.
- **Base de datos:** SQLite, SQLAlchemy.
- **IA:** Gemini mediante FastAPI; la clave solo existe en el entorno del backend.
- **Tipo de cambio:** API oficial SDDE del Banco Central de Costa Rica (BCCR), autenticada mediante token local.
- **Testing:** pytest.
- **Dependencias:** no se agregan paquetes frontend ni backend para esta refactorización; la autenticación y el cliente BCCR usan la biblioteca estándar de Python.

## Datos

- **Producto:** ID, nombre, categoría, precio CRC y existencias enteras.
- **Venta:** ID, producto, cantidad, fecha, total CRC, vendedor opcional, moneda/monto recibido, tasa y fecha BCCR, estado de pago.
- **Vendedor:** nombre único, acceso individual con contraseña derivada mediante `scrypt`, estado activo e indicadores de ventas.
- **Solicitud de aprobación:** tipo, datos, motivo, solicitante, decisión, revisor y fechas. Los tipos cubren cambios de precio, devoluciones, notas de crédito, cambio a USD/EUR y entradas de inventario.
- **Ajuste de venta:** devolución o nota de crédito aprobada, preservada como movimiento separado.
- **Movimiento de inventario:** entradas aprobadas, ventas y devoluciones revendibles.
- **Evento de auditoría:** actor autenticado, acción, entidad, detalles y fecha.
- **Seed:** mantiene exactamente las 50 ventas deterministas existentes. El seed no crea vendedores ni existencias ficticias; las ventas históricas quedan “Sin asignar” hasta asignarlas desde el panel.

## Reglas aprobadas para la operación

- El inventario comienza en cero; una venta nueva descuenta existencias y se rechaza si no hay unidades suficientes.
- Las entradas de inventario requieren solicitud y aprobación. Una devolución incrementa existencias solo si se marcó como revendible.
- Una devolución aprobada y una nota de crédito aprobada restan del ingreso bruto para calcular ingreso neto. Las devoluciones descuentan las unidades retornadas. El ticket promedio usa ingreso neto entre ventas confirmadas.
- Los cambios de precio, devoluciones, notas de crédito, pagos en divisa y entradas de inventario se aplican solo al aprobarse.
- Los pagos recibidos en USD usan la tasa de compra CRC/USD del BCCR; EUR usa la cotización EUR/USD publicada por BCCR multiplicada por la tasa de compra CRC/USD. El equivalente final se redondea a dos decimales con `ROUND_HALF_UP`.
- Una venta con cambio de moneda pendiente se excluye temporalmente de los indicadores. Si se deniega, se conserva el pago original sin modificaciones y vuelve a contarse.
- Solo José Castro puede resolver solicitudes, con contraseña local y conexión al backend desde loopback. El token de sesión expira a las ocho horas.

## API REST

- `GET /health`, `GET /productos`, `GET /ventas`, `GET /indicadores`.
- `POST /productos`, `PATCH /productos/{id}`, `DELETE /productos/{id}`.
- `POST /ventas`, `PATCH /ventas/{id}` (reasignación de vendedor por gerencia); las ventas no se borran del historial.
- `GET /vendedores`, `GET /vendedores/indicadores`, `POST /vendedores` (gerencia).
- `POST /auth/login`, `GET /auth/me`.
- `GET /tipos-cambio/{USD|EUR}?fecha=AAAA-MM-DD`.
- `POST /solicitudes`, `GET /solicitudes`, `POST /solicitudes/{id}/resolver`.
- `GET /inventario/movimientos`, `GET /auditoria`, `POST /chat`.

## Configuración privada

Copiar `.env.example` a `.env` y definir `MANAGER_PASSWORD`, `APP_AUTH_SECRET` y `BCCR_API_TOKEN`; configurar `GEMINI_API_KEY` para el chat. El BCCR entrega el token desde su servicio SDDE. `.env`, SQLite local, logs y build frontend están excluidos de Git.
