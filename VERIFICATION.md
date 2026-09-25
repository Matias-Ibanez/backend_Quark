# Verificación del prototipo

Estado comprobado el 24/09/2026 en la PC local. Este archivo registra pruebas reproducibles; los proyectos y medios usados en las pruebas viven en volúmenes Docker y no se suben a GitHub.

## Comprobaciones para repetir después de clonar

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8010/api/health
docker compose run --rm --no-deps -v "$PWD/tests:/app/tests:ro" studio python -m pytest tests -q -p no:cacheprovider
```

En Windows PowerShell, reemplazá el montaje de la última línea por `-v "${PWD}/tests:/app/tests:ro"`. El build del frontend ejecuta `next build` y la verificación de TypeScript.

## Resultado local

- `web`, `studio` y `hermes` arrancaron; `/api/health` devolvió `"status":"ok"`.
- Pasaron **21 pruebas** del backend y compiló el frontend con TypeScript.
- Hermes pudo leer las skills de QUARK y Manim y escribir en el directorio del proyecto del volumen compartido.
- Se exportó un video de ejemplo de **30,49 segundos**, vertical de 1080 × 1920, con audio AAC. Se revisaron fotogramas del inicio, desarrollo y cierre. Los clips previos de 5,97 y 10,6 segundos fueron retirados de la galería porque no cumplían el pedido de 30 segundos.
- Los mensajes guardados se revisaron después de la migración: no contenían rutas del contenedor, enlaces de archivo escritos en el texto ni imágenes base64.

La duración, el formato y la presencia de audio se verifican automáticamente. La calidad estética y la coherencia pedagógica del video siguen requiriendo revisión humana. `/api/costs` ofrece una estimación por tokens, no una factura; contrastala con `/api/deepseek/balance`.
