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

## Música y shorts automáticos

- Pasaron **28 pruebas** del backend en Docker, incluidas la validación y mezcla real de un tramo de audio, la selección del MP4 narrado de MoneyPrinterTurbo y el registro aproximado del costo. El frontend compiló con TypeScript tanto localmente como en Docker y `/chat` devolvió HTTP 200.
- El contenedor MoneyPrinterTurbo 1.3.7 arrancó sin exponer puerto al host. Su API respondió y reconoció DeepSeek V4 Flash y Pexels. La clave real quedó solo en `.env`, excluida de Git.
- Una petición real con solo el tema `Café de especialidad para una cafetería pequeña` generó clips de Pexels, voz y subtítulos. La primera integración descartó correctamente un MP4 mudo: MoneyPrinterTurbo entrega `combined_videos` sin voz y `videos` con voz. Tras corregir la selección, QUARK entregó **un único MP4 de 34,92 segundos**, 1080 × 1920, 21,5 MB y audio audible (pico -6,2 dB). Se inspeccionaron fotogramas a los 2, 7, 15, 25 y 33 segundos.
- Durante el render el contenedor de shorts usó aproximadamente 0,7–1,0 GB de su límite de 8 GB. El cuello de botella local fue CPU; elevar solo el límite de RAM no acelera el render.
- El saldo USD de DeepSeek observado antes y después de la segunda prueba se mantuvo en `1.76`; la API redondea ese dato y no permite atribuir un costo exacto a este short. `/api/costs` lo deja sin precio en vez de informar un cero engañoso. La mezcla musical automática con un video de Hermes se probó con FFmpeg; la combinación con un short real aún no se ejecutó.

## Brief guiado (26 de septiembre de 2026)

- `docker compose run --rm --no-deps -v ./tests:/app/tests:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`: **41 pruebas aprobadas**. Cubren la ausencia de llamadas al proveedor antes de confirmar, validación de opciones/HEX/texto obligatorio, versiones desactualizadas, consumo único de la confirmación, formato y duración en revisiones, contexto en el prompt y carruseles completos con SVG y PNG.
- El frontend pasó TypeScript y ESLint para el componente nuevo. Su imagen Docker compiló con `next build` y ambos servicios se desplegaron localmente.
- En el navegador se envió «Creame una imagen», se completaron los cuatro grupos de opciones y se revisó el resumen antes de confirmar. El tema fue café de especialidad; las elecciones fueron carrusel de tres láminas 1:1, estilo editorial, paleta cálida, serif, tono didáctico y sin fotografías.
- La generación real entregó tres SVG con sus PNG de **1080 × 1080**, conservando la secuencia en el chat. Las tres vistas se inspeccionaron sin cortes de texto y con la dirección visual elegida. La producción tardó **115,9 segundos**, con un costo estimado del proveedor de **USD 0,01743** por el carrusel; CPU y almacenamiento no están incluidos.
- El cambio se puede revertir con sus commits de backend y frontend sin eliminar conversaciones ni exportaciones: la tabla de briefs adicional puede quedar sin uso.
