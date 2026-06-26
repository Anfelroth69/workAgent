# test_runner

Endpoint HTTP para ejecutar scrapers + matcher dentro del contenedor
y devolver resultados vía HTTP. Usado para pruebas y validación del pipeline.

## Uso
GET /api/test — Ejecuta elempleo scraper + matcher, devuelve JSON
GET /api/health — Health check
