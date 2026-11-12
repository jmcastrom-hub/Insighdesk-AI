
## Configuración de Gemini y gestión de datos

- Copia `.env.example` a `.env` en la raíz y agrega una clave nueva de Gemini en `GEMINI_API_KEY`. No uses la clave compartida en el chat: revócala en Google AI Studio y genera otra.
- `start_dashboard.ps1` carga `.env` a las dos ventanas; el archivo está excluido de Git.
- La interfaz permite crear, editar y eliminar productos y ventas. Los ingresos de las ventas se recalculan al actualizar producto o cantidad. Un producto que ya tiene ventas no se puede borrar para conservar el historial; elimina primero las ventas asociadas si corresponde.
- El chat envía al backend la pregunta y una ventana corta de conversación. El backend adjunta indicadores, catálogo y ventas recientes; la clave nunca se envía al navegador.
