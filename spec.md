# Especificaciones Técnicas

## Stack Tecnológico
- **Frontend:** React + Vite, Recharts (para gráficos).
- **Backend:** FastAPI, Pydantic (validaciones).
- **Base de Datos:** SQLite, SQLAlchemy (ORM).
- **IA:** Integración futura con Gemini.
- **Testing:** pytest.

## Modelos de Datos
1. **Producto:** ID, Nombre, Categoría, Precio.
2. **Venta:** ID, Producto_ID, Cantidad, Fecha, Total.
3. **Seed:** Un script debe generar exactamente 50 ventas ficticias de forma idempotente (reproducible sin duplicar datos).

## Endpoints Requeridos (API REST)
- `GET /health`: Verificación de estado del servidor.
- `GET /productos`: Listado de productos.
- `GET /ventas`: Listado de ventas.
- `GET /indicadores`: Debe retornar JSON con: ingresos totales, cantidad total vendida, ticket promedio, y ventas agrupadas por categoría.
