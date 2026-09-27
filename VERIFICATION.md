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

## 2026-09-26 — Brief adaptativo

- Backend: 46 pruebas aprobadas; incluye generación directa para pedidos completos, preguntas persistidas limitadas a los datos faltantes, campos dependientes visibles, JSON inválido y duración pendiente.
- Frontend: TypeScript, ESLint del editor y build Docker de Next.js aprobados. Los pasos sin preguntas se omiten.
- Modelo real: un pedido de imagen cuadrada editorial cálida sobre café no pidió campos; evaluación estimada USD 0.00030855. Un reel sobre café detectó solo duración en la prueba del evaluador. La prueba desde el chat detectó que los defaults podían confundirse con datos aportados; se aclaró el prompt y se agregó validación de duración no aportada ni delegada.
- Reversión: revertir el cambio de brief adaptativo en backend y editor frontend; la tabla adicional brief_questions puede quedar sin uso sin borrar proyectos ni archivos.
- Chat real tras la corrección: el pedido de reel mostró únicamente Duración del video, paso 1/2; al guardar pasó a revisar solo esa respuesta. Se canceló antes de producir. Captura local ignorada: `.tmp/brief-adaptativo.png`. El primer render de prueba anterior se interrumpió al desplegar la corrección.

## 2026-09-26 — Identidad y acompañamiento de marketing

- `docker compose run --rm --no-deps -v ./backend:/app/backend:ro -v ./tests:/app/tests:ro -v ./hermes/SYSTEM.md:/app/SYSTEM.md:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`: 76 pruebas aprobadas, una advertencia de deprecación existente de Starlette.
- Se verificaron identidad, capacidades, proceso, inicio, recursos visuales, fotos, textos, campañas, música, iteraciones, límites y expectativas de Instagram; los pedidos concretos o mixtos conservan su ruta de producción. Programación sigue fuera de alcance.
- Las respuestas frecuentes no llaman al proveedor, crean briefs ni registran consumo de generación. Se probó la ruta de ejecución de chat sin credencial para una pregunta de capacidades.
- Docker studio reconstruido y desplegado. Prueba HTTP real a través de localhost:8010: quién sos, qué puedes hacer, cómo empezamos e Instagram recibieron cuatro respuestas distintas, sin medios ni brief. Salud del stack: ok.
- El perfil público se comparte entre respuestas inmediatas y el contexto del modelo. No se modificaron herramientas, exportaciones SVG/PNG ni frontend.
- Reversión: revertir este cambio en marketing_profile, guardrails, agent, workspace y SYSTEM.md junto con sus pruebas/documentación; no requiere migraciones ni eliminar conversaciones.

## 2026-09-26 — Adjuntos dentro del mensaje

- Backend: 78 pruebas aprobadas. Las imágenes enviadas se guardan como referencias de medios del mensaje del usuario, no solo como recursos globales del proyecto. Se verificó devolución por historial, descarga de la imagen y conservación después de inicializar la base.
- Producción, respuestas directas y brief usan el mismo guardado del turno con sus adjuntos. La API y la tabla messages mantienen el contrato existente, sin migraciones.
- Reversión: revertir add_user_message y sus llamadas/tests; los mensajes existentes y archivos siguen almacenados. El frontend anterior puede ignorar esos medios sin romper la conversación.

## 2026-09-26 — Detalles editables y lenguaje claro

- Suite backend completa en Docker: 85 pruebas aprobadas, con una advertencia existente de Starlette. Comando: `docker compose run --rm --no-deps -v ./backend:/app/backend:ro -v ./tests:/app/tests:ro -v ./hermes/SYSTEM.md:/app/SYSTEM.md:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`.
- Se verificaron texto exacto solicitado con modo automático, guardado parcial antes de preguntas posteriores, confirmación incompleta rechazada, conservación de colores/texto para la revisión, recuperación de un intento automático fallido y cambio de tipo de pieza con duración/láminas disponibles.
- Interfaz, respuestas, errores y política del agente usan términos cotidianos. El filtro de respuestas también sustituye el término anterior; las rutas y claves del contrato HTTP se conservan.
- Prueba real por HTTP y navegador: imagen sin contexto abre preguntas sin llamar al proveedor; guardado parcial con colores/texto pendientes devuelve inputs editables. Se completaron las etapas y el resumen conservó el texto y los colores. No se inició una generación para esta comprobación. Captura ignorada: `.tmp/detalles-texto-editable.png`.
- Reversión: revertir los cambios de esta unidad en backend/brief.py, backend/guardrails.py y hermes/SYSTEM.md, con sus pruebas y documentación. No modifica el esquema ni elimina conversaciones, SVG o PNG.

## 2026-09-26 — Contenido desde documentos PDF

- Snapshot exacto de la unidad preparada en el índice, exportado con `git checkout-index --all --prefix=.tmp/pdf-stage/`: **97 pruebas aprobadas** en Docker. Comando: `docker compose run --rm --no-deps -v ./.tmp/pdf-stage/backend:/app/backend:ro -v ./.tmp/pdf-stage/tests:/app/tests:ro -v ./.tmp/pdf-stage/hermes/SYSTEM.md:/app/SYSTEM.md:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`. Una advertencia existente de Starlette.
- Se ejercitaron PDF digitales y escaneados reales, una portada digital con página escaneada, portada PNG, conservación del adjunto en su turno/proyecto, límite de páginas/texto, archivos corruptos y limpieza ante timeout. El contexto de evaluación incluye un extracto; Hermes recibe el original, texto y estados de lectura junto con la instrucción de cargar quark-documents.
- Runtime: API reconstruida con Poppler y Tesseract; Compose monta quark-documents y se verificó su lectura dentro de Hermes. Por navegador se subió un PDF de café con descuento del 15%, se abrió su portada y se pidió un video vertical de 10 segundos. Entregó un único MP4 de **1080×1920 y 10,000 segundos**, sin audio como se pidió. El plan y el fotograma de los 4 s conservan el descuento del documento. Tardó **298,03 s** y registró costo estimado **USD 0,04098311**, sin CPU ni almacenamiento.
- Los originales, texto, metadatos y exportaciones permanecen en el volumen de datos y fuera de Git. El OCR está acotado a 12 páginas que necesiten reconocimiento; el texto, a 120.000 caracteres. La información parcial no equivale a lectura completa.
- Reversión: quitar la extracción/contexto PDF de documents, app, agent, brief y store junto con paquetes/montaje y guía quark-documents. Revertir su documentación y respuestas de capacidades; conservar el volumen. No modifica imágenes, SVG/PNG ni mensajes anteriores.

## 2026-09-26 — Preguntas dentro de la conversación

- Suite completa en Docker: **100 pruebas aprobadas**. Comando: `docker compose run --rm --no-deps -v ./backend:/app/backend:ro -v ./tests:/app/tests:ro -v ./hermes/SYSTEM.md:/app/SYSTEM.md:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`. Una advertencia existente de Starlette.
- GET conserva fields/answers y agrega question/answered. PUT con field registra la respuesta individual; POST brief/reply permite responder por texto, opciones, proporciones y cantidades sin llamadas al proveedor. Se verificaron progreso tras recarga, versiones desactualizadas, texto vacío, FAQ y rechazo de programación sin consumir la pregunta, cancelación y confirmación única.
- Cada pregunta queda como mensaje del agente y cada respuesta como mensaje del usuario, para conservar también los roles correctos en el contexto. La confirmación queda como una acción explícita en el historial; Hermes y shorts no vuelven a guardar el pedido inicial. La producción automática conserva su turno de usuario. Un pedido natural de short puede seleccionar su ruta sin selector de función.
- Runtime por navegador: se envió una imagen sin tema, se respondió desde el compositor, se eligió Cuadrado 1:1, se recargó y se conservó la revisión final. Se canceló la prueba sin generar una pieza. Las respuestas permanecen en los mensajes. API y frontend reconstruidos en Docker; salud ok.
- Reversión: quitar brief_responses y el contrato question/answered/reply junto con la integración del editor conversacional. Se pueden dejar las tablas adicionales sin uso; no borrar conversaciones ni archivos. Revertir record_user en agent/shorts junto con el registro de confirmación para recuperar el comportamiento anterior.

## 2026-09-26 — Aclaraciones sin atribuir decisiones al usuario

- Pruebas enfocadas: **25 aprobadas**, una advertencia existente de Starlette. Comando: `docker compose run --rm --no-deps -v ./backend:/app/backend:ro -v ./tests:/app/tests:ro -v ./hermes/SYSTEM.md:/app/SYSTEM.md:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests/test_brief.py tests/test_inline_questions.py`.
- Tres pedidos mínimos de imagen/video prueban el evaluador real sin proveedor: tema vacío, primera pregunta subject, campos subject/aspect, estado draft y ausencia de producción. La introducción ya no afirma que el usuario dejó decisiones a criterio del agente. SYSTEM distingue propuestas automáticas de preferencias o delegaciones explícitas.
- Runtime: studio reconstruido y desplegado, sin ejecuciones activas al reiniciar. POST chat a través de localhost:8010 con «Generame una imagen» devolvió «¡Entendido! Antes de crear, necesito algunos datos. Vamos a definirlos con estas preguntas.», question=subject y fields=subject,aspect. Se canceló la prueba sin generar contenido ni llamar al proveedor.
- Reversión: revertir la frase de adaptive_start, la aclaración en SYSTEM, las pruebas y documentación de esta unidad. No cambia el contrato, datos, preguntas, archivos ni frontend.
