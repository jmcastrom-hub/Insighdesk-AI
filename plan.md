# Plan de Ejecución

- [x] **Fase 1: Inicialización y Estructura**
  - Estructura React + Vite y FastAPI con `/health`.
  - `package.json`, `requirements.txt`, README y repositorio Git.

- [x] **Fase 2: Base de Datos, Modelos y API Core**
  - SQLite, SQLAlchemy, entidades Producto/Venta y seed determinista de 50 ventas.
  - Validaciones Pydantic, endpoints REST e indicadores.
  - Evidencia previa: pytest 6 passed.

- [x] **Fase 3: Dashboard Frontend**
  - React consume `/indicadores`; gráficos Recharts e indicadores.
  - Evidencia previa: build Vite correcto y dashboard con datos seed.

- [x] **Fase 4: Agente IA**
  - Gemini conectado mediante FastAPI y chat React con opciones de consulta y tono conversacional.
  - La clave se configura en `.env` y nunca se envía al navegador.
  - Límite de evidencia: el endpoint está implementado, pero la respuesta en vivo de Gemini no se ha confirmado en este equipo; ver `docs/bitacora-validacion.md`.

- [x] **Fase 5: Operación, Auditoría y Aprobaciones**
  - Paleta azul y selector barras/pastel en ambas visualizaciones de ingresos por categoría.
  - Vendedores con acceso individual y métricas; seed queda “Sin asignar” hasta importar los nombres y asignaciones reales.
  - Inventario con entradas aprobadas, movimientos, descuento por venta y devolución revendible. Las existencias inician en cero, sin inventar cantidades.
  - Registro de devoluciones, notas de crédito, cambios de precio y conversión USD/EUR como solicitudes; solo gerencia las puede aprobar o denegar desde una conexión local.
  - Ingresos netos, unidades y métricas por vendedor incorporan ajustes aprobados. Una venta sale de los indicadores mientras su cambio de pago está pendiente; si se deniega, conserva y cuenta el pago original.
  - Conversiones usan las series BCCR, guardan tasa/fecha y convierten USD por compra CRC/USD y EUR por EUR/USD × compra CRC/USD; redondeo a dos decimales `ROUND_HALF_UP`.
  - Agregados autenticación, auditoría, migración SQLite compatible y documentación. Sin agregar dependencias.
  - Verificación de implementación: pytest **12 passed**; `compileall` correcto; `npm.cmd run build` correcto (**443 módulos**). Vite reporta bundle JS de 687.07 kB, por encima del umbral informativo de 500 kB.
  - Pendiente para operación real: configurar `MANAGER_PASSWORD`, `APP_AUTH_SECRET`, token BCCR y Gemini en `.env`; cargar vendedores y existencias reales; asignar las 50 ventas seed.

- [x] **Ajustes de dashboard y datos de demostración**
  - Corregir ambos gráficos circulares de ingresos con datos numéricos y proporciones de Recharts; mantener la dona cuadrada en tamaños de pantalla distintos.
  - Añadir movimiento visual moderado con estados hover/transiciones y respetar `prefers-reduced-motion`.
  - Agregar seed idempotente claramente marcado con seis vendedores ficticios, seis ventas vinculadas y movimientos de inventario para explorar los espacios Vendedores, Ventas e Inventario. Las 50 ventas originales permanecen sin asignar.
  - Configurar el acceso local de gerencia con el valor indicado por el usuario y compartirlo con las cuentas de demostración, guardando solo hashes de contraseñas de vendedores y manteniendo `.env` fuera de Git.
  - Verificación: pytest **13 passed**; build Vite correcto (**443 módulos**). El bundle minificado continúa sobre el aviso informativo de 500 kB.
  - No se reescribió el historial: `3e4bbc9` sigue siendo antecesor de `main`; Git organiza commits en el historial, no dentro de directorios.

## Evidencia

Los cambios, decisiones aprobadas, comandos y limitaciones comprobadas están descritos en `docs/bitacora-validacion.md`. Los secretos, base SQLite, dependencias locales y logs no se guardan en Git.

- [x] **Recuperación del entorno activo**
  - Detectada y reiniciada la instancia antigua de Uvicorn: servía código previo, devolvía 404 para login/vendedores y mantenía variables de entorno anteriores.
  - Confirmadas rutas API con HTTP 200, autenticación de gerente, seis vendedores y sus seis ventas demo; las 50 ventas originales siguen sin asignar.
  - El resumen principal ahora incluye ranking de seis vendedores, barras de progreso, encabezado con total de transacciones y animaciones suaves con soporte de movimiento reducido.
  - Evidencia: pytest **13 passed**, build Vite correcto (**443 módulos**), endpoints reales 200; `GET /indicadores` refleja 56 ventas.

- [x] **Historial demo y dinamismo en todos los espacios**
  - Añadir ocho aprobaciones de demostración con cuatro aprobadas y cuatro denegadas, etiquetadas claramente y resueltas por las reglas de negocio existentes. Los efectos de las aprobadas quedan reflejados en ajustes e inventario; las denegadas no modifican datos.
  - Mostrar el historial con línea de tiempo, estados, distintivo de muestra, filtros por decisión y búsqueda contextual.
  - Añadir indicadores de contexto y mejoras de interacción a productos, ventas, inventario, vendedores, aprobaciones y auditoría.
  - Evidencia final: pytest **14 passed**; Vite build correcto (443 módulos); historial API 8/4/4 y endpoints 200.
