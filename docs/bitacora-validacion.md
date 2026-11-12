# Bitácora de implementación y validación

Fecha del registro: 12 de noviembre de 2026.

Este registro resume las comprobaciones ejecutadas durante las fases de dashboard, CRUD y agente. No incluye claves, archivos `.env`, bases de datos locales ni logs sin filtrar.

## Resultado de la implementación

- Dashboard React + Vite consume `GET /indicadores` y muestra los KPI y gráficos de ingresos por categoría.
- El backend FastAPI ofrece altas, edición y eliminación de productos y ventas. Los totales de venta se recalculan al editar la cantidad o el producto.
- El chat React llama a `POST /chat`; FastAPI construye el contexto con datos persistidos y llama a Gemini por REST. La clave se lee desde `.env` en el backend.

## Verificaciones exitosas

- Backend: `pytest -q` → **6 passed**.
- Backend: `python -m compileall -q app tests` → correcto.
- Frontend: `npm run build` → correcto, **442 módulos transformados**. Vite informó que el bundle JavaScript minificado supera 500 kB; la compilación terminó sin error.
- Navegador: captura de Chrome mostró el dashboard con los datos persistidos del seed: ingresos CRC 768 875, 210 unidades, ticket promedio CRC 15 377,50 y 50 transacciones.
- HTTP: Vite `/` y FastAPI `/indicadores` respondieron **200**; el preflight CORS para el origen local de Vite permitió `PATCH`.
- Smoke test REST en SQLite temporal: health, crear/editar/eliminar producto y venta respondieron como se esperaba; se rechazó borrar un producto con ventas asociadas.
- Chat sin clave: `POST /chat` devolvió **503** controlado y no expuso credenciales.

## Incidencias encontradas y cambios

1. La pantalla sin datos fue causada por CORS: el navegador bloqueaba la petición de React a FastAPI. Se agregó CORS para `localhost:5173` y `127.0.0.1:5173`.
2. La optimización CommonJS de Vite necesitaba imports explícitos de React en los componentes JSX. Se añadieron.
3. El gráfico circular no se dibujaba en el navegador. Se sustituyó por una dona calculada con los ingresos recibidos del API.
4. Un segundo Vite fallaba porque el puerto 5173 ya estaba ocupado. El script de inicio ahora reutiliza el frontend activo.
5. El reinicio del backend intentó detener el PID obsoleto `34080`. Se ajustó el script para buscar el proceso Python configurado; el PID obsoleto se omite.
6. El endpoint Gemini agotó el tiempo de espera en las pruebas manuales. Desde la terminal del usuario, `Test-NetConnection generativelanguage.googleapis.com -Port 443` dio `TcpTestSucceeded: True`, pero eso solo verifica conectividad TCP, no que Gemini acepte la clave ni que genere una respuesta.

## Estado del agente

La integración del endpoint, el contexto de negocio, el chat y el manejo de errores están implementados. **La respuesta real de Gemini no se ha validado exitosamente**: el chat mostró timeout durante la comprobación y no se debe presentar como una llamada funcional confirmada. La clave local está ignorada por Git. El backend fue detenido por comando al final de la sesión para permitir reiniciarlo desde la terminal del usuario.

## Logs y secretos

Los archivos `backend-start.log`, `backend-error.log`, `frontend-start.log`, `frontend-error.log` y `debug.log` son salidas locales efímeras y no se incluyen en el commit. `.gitignore` ahora los excluye; los eventos relevantes y los resultados comprobables quedan resumidos en esta bitácora. `.env`, la SQLite local y las dependencias/build locales también se excluyen.

## Refactorización del Dashboard — 12 de noviembre de 2026

### Cambios

- Reemplacé los acentos verdes por una paleta azul y añadí selectores de barras/pastel en ambos gráficos de categorías.
- Añadí perfiles con contraseña para vendedores, métricas por persona, asignación de las ventas seed, existencias y movimientos de inventario.
- Las ventas nuevas requieren existencias suficientes y quedan asignadas al usuario vendedor autenticado. Seed permanece sin vendedor y stock 0 hasta cargar información real.
- Añadí solicitudes visibles de cambio de precio, entrada de inventario, devolución, nota de crédito y pago en USD/EUR. José Castro aprueba o deniega con su contraseña, desde la conexión loopback; se guarda actor, motivo, decisión y hora.
- Los pagos en moneda extranjera quedan fuera de indicadores mientras están pendientes. Si el cambio se deniega, el pago original se mantiene y vuelve a contarse; la aprobación guarda tasa y fecha BCCR y el equivalente CRC.
- Devoluciones y notas aprobadas restan del ingreso neto; las unidades devueltas solo regresan al inventario cuando se marcan revendibles. Se bloquean ajustes que superen el importe de la venta.
- La bitácora conserva vendedor, acción, registro y detalles. Se amplió el contexto de Gemini con inventario, vendedores, ajustes y solicitudes pendientes, y se añadieron preguntas sugeridas.
- Actualicé `intent.md`, `spec.md`, `plan.md`, `README.md` y este archivo con las reglas aprobadas, el alcance y la configuración local. No agregué dependencias.

### Verificaciones ejecutadas

- Backend: `python -m pytest -q` → **12 passed**. Incluye seed, validaciones, stock, ventas, indicadores, ajustes aprobados/denegados, sesión vendedor/gerente, acceso de gerente solo local, migración de SQLite existente y conversión USD/EUR simulada con tasa BCCR.
- Backend: `python -m compileall -q app tests` → correcto.
- Frontend: `npm.cmd run build` → correcto, **443 módulos transformados**. Vite reportó bundle JS de **687.07 kB** minificado (umbral informativo 500 kB).
- No se añadió `httpx2` ni otra dependencia para pruebas HTTP; las pruebas pytest llaman las funciones de handlers/negocio directamente.
- La llamada en vivo a BCCR no pudo validarse porque no se configuró `BCCR_API_TOKEN`; la conversión no usa tasas manuales y falla de forma explícita si falta el token.
- La respuesta real de Gemini sigue sin verificación en vivo, como se documentó arriba.

### Fuente oficial del cambio

El backend usa el endpoint SDDE documentado por el [BCCR](https://gee.bccr.fi.cr/indicadoreseconomicos/Documentos/DocumentosMetodologiasNotasTecnicas/Estandar_API_SDDE.pdf), que requiere token Bearer. La documentación del [Web Service de Indicadores Económicos del BCCR](https://gee.bccr.fi.cr/indicadoreseconomicos/Documentos/DocumentosMetodologiasNotasTecnicas/Webservices_de_indicadores_economicos.pdf) identifica 317 como compra y 318 como venta CRC/USD. La regla aplicada para pagos recibidos en divisa es la de compra, según aprobación del usuario.

### Configuración operativa pendiente

1. Copiar `.env.example` a `.env`; definir `MANAGER_PASSWORD`, un `APP_AUTH_SECRET` independiente y el token local de BCCR. Agregar la clave de Gemini si se habilitará el chat.
2. Crear cuentas con los nombres/contraseñas reales de vendedores; asignarles las 50 ventas seed.
3. Registrar las existencias reales mediante solicitudes de entrada y aprobación. No se inventaron nombres ni cantidades.

## Ajustes visuales y datos demo - 12 de noviembre de 2026

### Cambios aplicados

- Los dos graficos circulares usan `PieChart` de Recharts con ingresos convertidos a numeros y categorias sin valor cero filtradas. La dona tiene un marco cuadrado con proporcion fija para no deformarse en paneles estrechos.
- Se agregaron transiciones suaves a tarjetas, navegacion y selectores; la animacion se reduce si el sistema tiene `prefers-reduced-motion` activado.
- Seed idempotente independiente `operations-demo-v1`: seis cuentas ficticias (Ana Rodriguez, Luis Morales, Maria Fernanda Soto, Carlos Jimenez, Sofia Vargas y Diego Ramirez), seis ventas vinculadas, seis entradas de inventario y seis salidas por venta. La bitacora marca las operaciones como demo.
- Las 50 ventas anteriores no se reasignaron. El seed nuevo requiere `DEMO_SELLER_PASSWORD` o `MANAGER_PASSWORD`; el backend persiste hashes y la contrasena queda solo en `.env` local, ignorado por Git.
- La clave de gerente se establecio localmente desde la solicitud del usuario. `.env` y la base SQLite no se agregaron al repositorio.

### Verificacion

- `python -m pytest -q --tb=short -p no:cacheprovider --basetemp=./.pytest-tmp-codex` -> **13 passed**.
- `npm.cmd run build` -> correcto, 443 modulos transformados. El bundle JS minificado es 687.24 kB; Vite presenta el aviso informativo de 500 kB.
- `3e4bbc9` se verifico como antecesor de `HEAD` en `main`. Git almacena commits en el historial, no como carpetas.

## Correccion de instancia activa - 12 de noviembre de 2026

- Causa observada: el dashboard usaba procesos Vite/Uvicorn anteriores al codigo y al `.env` actual. La API antigua devolvia 404 en login y endpoints de vendedores; por eso no coincidian ni la clave ni los espacios de datos.
- Reinicie Uvicorn del proyecto con el `.env` actual. La API en vivo respondio 200 en `/health`, `/indicadores`, `/productos`, `/ventas`, `/vendedores`, `/vendedores/indicadores` y `/inventario/movimientos`.
- Inicio de sesion de gerente validado contra la API; no se imprimio clave ni token.
- La API y la SQLite local reportan 56 ventas (50 originales + 6 demo), 6 vendedores, 8 productos y 12 movimientos de inventario.
- Vite en `localhost:5173` sirve el modulo con el ranking y los estilos nuevos. El resumen muestra ahora seis vendedores con metricas y barras, encabezado destacado y movimiento de entrada; se debe recargar el navegador para recibir HMR.
- Verificacion tras el cambio visual: pytest **13 passed**; `npm.cmd run build` correcto (**443 modulos**). Bundle minificado 690.17 kB con aviso informativo de Vite.

## Historial de aprobaciones y pulido de espacios - 12 de noviembre de 2026

- Seed idempotente `approvals-demo-v1` agrega ocho solicitudes históricas de muestra (4 aprobadas y 4 denegadas) de precio, inventario, devolución y nota de crédito. Cada una queda etiquetada `DEMO-HISTORY-v1`, incluye solicitante/respuesta DEMO y revisor `DEMO | Jose Castro`.
- Las decisiones se ejecutan a través de `resolver_solicitud` y `_apply_request`: cambios aprobados actualizan producto, existencias e ingreso neto; las denegadas no producen cambios. No se fabricaron registros de cambio USD/EUR que requirieran tasas BCCR.
- La bitácora de aprobaciones, ajustes y auditoría es visible desde las vistas existentes. Se añadieron búsqueda por texto y filtros de estado en la vista de aprobaciones.
- Todos los espacios de administración muestran tarjetas de contexto, conteos, estados, navegación de búsqueda, estados vacíos y animaciones de entrada/hover con soporte para movimiento reducido.
- Verificación local: `14 passed`; build Vite correcto (443 módulos, bundle 694.34 kB con aviso informativo del límite); API `GET /solicitudes` y `/auditoria` 200; historial 8/4/4; 6 vendedores, 56 ventas y 14 movimientos.
- El historial Git solicitado se consolidó en la refactorización existente. Para cambiar el árbol de un commit Git recalcula su SHA; se conserva el título y el commit Dashboard anterior como ancestro.
