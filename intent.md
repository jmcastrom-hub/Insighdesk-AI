# Propósito del Proyecto: Insightdesk-AI

Insightdesk-AI es una plataforma Full Stack para consultar el desempeño de ventas, mantener productos e inventario, y solicitar cambios con trazabilidad. Un asistente Gemini responde preguntas de negocio usando los datos guardados.

## Criterios de éxito

- FastAPI sirve datos validados desde SQLite mediante SQLAlchemy.
- React + Vite consume la API y presenta indicadores con Recharts.
- El seed mantiene sus 50 ventas de demostración reproducibles; no asigna vendedores ni inventario ficticios.
- Productos, ventas, vendedores, existencias, devoluciones, notas de crédito y pagos en divisa se reflejan de forma consistente en los indicadores.
- Las acciones de vendedor y gerente se registran en una bitácora; cambios financieros sensibles requieren decisión del gerente José Castro.
- Los pagos USD/EUR aprobados guardan la tasa oficial BCCR, su fecha y su equivalente CRC.
- Las pruebas pytest cubren validaciones, indicadores, inventario, auditoría y flujos de aprobación.
- La clave de Gemini, el token BCCR y las credenciales locales permanecen fuera de Git.
