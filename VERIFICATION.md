# Verificación del prototipo

Estado comprobado el 25/09/2026 en la PC local con los repositorios separados. Este archivo registra pruebas reproducibles; los proyectos y medios usados en las pruebas viven en volúmenes Docker y no se suben a GitHub.

## Comprobaciones para repetir después de clonar

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8011/api/health
docker compose run --rm --no-deps -v "$PWD/tests:/app/tests:ro" studio python -m pytest tests -q -p no:cacheprovider
```

En Windows PowerShell, reemplazá el montaje de la última línea por `-v "${PWD}/tests:/app/tests:ro"`. Desde `landing-quark`, `docker compose up -d --build` inicia el frontend y `curl -fsS http://127.0.0.1:8010/api/health` comprueba el proxy entre repositorios. Su build ejecuta `next build` y la verificación de TypeScript.

## Resultado local

- `studio` y `hermes` arrancaron desde este repositorio; `web` arrancó desde `landing-quark`. La API respondió en `127.0.0.1:8011` y mediante el proxy de Next.js en `127.0.0.1:8010` con `"status":"ok"`. `/chat` devolvió HTTP 200.
- Pasaron **23 pruebas** del backend, incluidos saludo sin llamada al modelo, aclaración de briefs incompletos y entrega de preguntas de Hermes sin archivo final. El frontend separado compiló con TypeScript, tanto localmente como en su imagen Docker.
- Hermes pudo leer las skills de QUARK y Manim y escribir en el directorio del proyecto del volumen compartido.
- Se exportó un video de ejemplo de **30,49 segundos**, vertical de 1080 × 1920, con audio AAC. Se revisaron fotogramas del inicio, desarrollo y cierre. Los clips previos de 5,97 y 10,6 segundos fueron retirados de la galería porque no cumplían el pedido de 30 segundos.
- Los mensajes guardados se revisaron después de la migración: no contenían rutas del contenedor, enlaces de archivo escritos en el texto ni imágenes base64.

La duración, el formato y la presencia de audio se verifican automáticamente. La calidad estética y la coherencia pedagógica del video siguen requiriendo revisión humana. `/api/costs` ofrece una estimación por tokens, no una factura; contrastala con `/api/deepseek/balance`.

## Publicaciones SVG

- Pasaron **25 pruebas** del backend en Docker, incluidas la entrega de SVG con vista PNG y el rechazo de elementos ejecutables o recursos externos. El frontend compiló con TypeScript y se desplegó junto al backend.
- Las tres plantillas vectoriales (editorial, producto y tipográfica) se validaron y renderizaron con Playwright/Chromium. También se verificó la incrustación de una imagen local dentro del SVG y el rechazo de una imagen faltante.
- Una solicitud real al agente produjo una publicación editorial en SVG de 2,7 KB con ocho elementos de texto vectorial y siete rectángulos; la vista PNG se revisó visualmente. El chat recibió el SVG, la galería conservó el PNG de vista previa y la API respondió con `status: ok` a través del frontend.
