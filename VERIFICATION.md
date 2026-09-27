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

## 2026-09-26 — Dirección visual y motor de video

- Suite completa: **117 pruebas aprobadas**, una advertencia existente de Starlette. Comando: `docker compose run --rm --no-deps -v ./backend:/app/backend:ro -v ./tests:/app/tests:ro -v ./hermes/SYSTEM.md:/app/SYSTEM.md:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`.
- Se verificaron preguntas ante shorts ambiguos aunque el modelo adivine clips, respuestas por texto/botones, persistencia, ruta de producción tras confirmar, animación explícita sin repetir la pregunta, cambio de dirección en revisiones y fotos propias solo cuando existen. Shorts/reels conservan 9:16 por defecto o una proporción solicitada expresamente. El frontend consume los campos nuevos sin cambiar su contrato.
- FFmpeg real verifica montaje cuadrado, encuadre 4:5 conservando subtítulos, retiro de voz y ajuste sincronizado de duración. No se entrega un video cuya duración requiera un factor fuera de 0,8–1,25. Los clips se describen como referencias, y el guion recibe la instrucción de no atribuir escenas de stock al negocio ni inventar ventajas.
- Runtime por navegador: «Haceme un short de 20 segundos sobre por qué somos una buena cafetería» mostró las dos direcciones y luego pidió características confirmadas. Se eligieron clips y se aportaron los datos de una cafetería de demostración. MoneyPrinterTurbo produjo un MP4 real de 16,610 s, que la validación anterior rechazó. La adaptación corrigió el resultado a **19,988 s, 1080×1920 y audio**; se abrió en la vista previa del chat y se verificó su metadata.
- Para probar la adaptación se reutilizó la tarea ya terminada de MoneyPrinterTurbo: el POST de creación se sustituyó en el harness por su ID, pero la consulta, descarga, ajuste, entrega y registro de ejecución fueron reales. No se repitió el guion ni la búsqueda de clips ni se atribuyó un costo cero a la generación original. Una prueba previa de encuadre 4:5 queda también en la conversación de demostración. Captura ignorada: `.tmp/quark-video-direction.png`.
- Reversión: revertir video_mode, su evaluación/preguntas, la selección de ruta en agent/shorts, la adaptación local y la guía de SYSTEM/quark-marketing con sus pruebas/documentación. No cambia tablas ni elimina conversaciones, fotos o exportaciones; el modo anterior conserva la ruta legacy.

## 2026-09-26 — Guiones de marketing con voz

- Se revisaron opciones en skills.sh y sus fuentes. Se adaptó `scriptwriting` de GTM Agents, revisión `78e0419f4440bcb43bc80127e174ecf5adef1753`, con licencia Apache-2.0 y atribución preservadas. `quark-narration` agrega locución en español, concreción, revisión de relleno, evidencia confirmada y sincronización con la voz. La licencia se conserva en la skill y en la imagen de la API.
- Pruebas enfocadas: **14 aprobadas**. Suite de la imagen final: **125 aprobadas**, una advertencia existente de Starlette. Comando final: `docker compose run --rm --no-deps -v ./tests:/app/tests:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`. Se comprobó inyección en Hermes solo para videos con voz, conservación de texto exacto, datos/CTA en MoneyPrinterTurbo, límites de 2.000 caracteres y exportación MP4 con FFmpeg real.
- Runtime: tres solicitudes de guion a DeepSeek con datos de una cafetería ficticia, siguiendo la estructura de prompt de MoneyPrinterTurbo. Borrador anterior: 40 palabras; primera adaptación: 41; adaptación final: 38 para el objetivo de 20 segundos. Se reforzó la eliminación de relleno después del primer resultado. No se sintetizó audio ni renderizó otro video para esta comparación; conteo de palabras no prueba duración ni calidad de locución. Un caso no demuestra una mejora general de calidad. Costos auxiliares registrados como `narration_validation_*`, suma estimada **USD 0,00335243**; originales en el volumen y harness en `.tmp`, fuera de Git.
- API reconstruida y Compose actualizado sin tareas activas antes de reiniciar. Hermes verificó mediante sus funciones nativas `skills_list` y `skill_view` que la skill aparece y carga la guía y las comprobaciones de duración. `/api/health` por localhost:8010 devolvió ok. No se agregó proveedor ni llamada extra en el flujo de producción; sí texto de contexto. No se cambió frontend, SVG/PNG, credenciales, datos ni esquema de memoria.
- Reversión: revertir `backend/narration.py`, su uso en agent/shorts, la skill y su indicación en quark-marketing, sus COPY/montaje, pruebas y documentación; reconstruir studio y recrear Hermes. No requiere migraciones ni borrar conversaciones o medios.

## 2026-09-26 — Skill Manim Community de adithya-s-k

- Instalación con `skill-installer/scripts/install-skill-from-github.py --repo adithya-s-k/manim_skill --path skills/manimce-best-practices --ref cef045011722d285692e3381d12d4d637da56e18 --dest hermes/skills`. Solo se incorporó Community Edition. Reglas, ejemplos, plantillas y licencia MIT permanecen sin cambios; SKILL.md agrega metadata y el perfil QUARK Docker. Procedencia y modificaciones registradas en UPSTREAM.md.
- `quick_validate.py hermes/skills/manimce-best-practices`: skill válida. Suite de la imagen reconstruida: **127 pruebas aprobadas**, una advertencia existente de Starlette. Comando: `docker compose run --rm --no-deps -v ./tests:/app/tests:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`. Se verificaron instrucciones de carga de la nueva skill en videos animados y montaje con originales, combinación con locución y conservación de texto exacto y datos. Las imágenes no reciben el bloque específico de animación.
- Runtime: Compose recreado sin tareas activas, API saludable por localhost:8010. `skills_list`/`skill_view` nativos verificaron la skill, perfil y lectura de `rules/positioning.md`, con `setup_needed=False`. Se analizaron los 12 archivos Python del paquete sin errores de sintaxis.
- Render real en Hermes con Manim 0.20.1: `manim --renderer cairo -r 320,180 --fps 12 --media_dir /tmp/quark-manim-ce-nyw2jc9t <source> <scene>`. La plantilla `templates/basic_scene.py / YourScene` produjo **8,000 s**; `examples/graph_plotting.py / BasicAxes` produjo **2,000 s**, incluidos números y etiquetas LaTeX. Ambos MP4 tienen 320×180. Se inspeccionaron fotogramas al 20%, 50% y 80%; captura local ignorada `.tmp/manim-ce-smoke.png`. Son pruebas de compatibilidad de ejemplos, no anuncios finales ni una evaluación de calidad del modelo. No se usó LLM ni TTS para estas pruebas.
- La skill se monta de solo lectura. No agrega dependencias, GPU, proveedor, migración ni cambios a frontend o SVG/PNG. Las consultas de skill/referencias que haga el agente forman parte de sus turnos/contexto habituales y pueden aumentar consumo; los ejemplos genéricos no sustituyen los datos de marca ni el formato pedido.
- Reversión: quitar el paquete manimce-best-practices y su montaje; revertir las indicaciones en agent, SYSTEM y quark-marketing, pruebas y documentación; reconstruir studio y recrear Hermes. La skill nativa anterior permanece disponible en Hermes, y los datos y videos existentes se conservan.


## Remotion runtime y skills oficiales

- Instalación con `skill-installer/scripts/install-skill-from-github.py --repo remotion-dev/skills --path skills/remotion-best-practices --ref cf49eff5d4463b33966b6618c83f7295797dd028 --dest hermes/skills`. Referencias pertinentes de creación, layout, markup, render y subtítulos conservadas; se omiten mapas y guías de infraestructura ajenas al prototipo, perfil QUARK Docker y atribución en UPSTREAM.md. `quick_validate.py hermes/skills/remotion-best-practices`: **skill válida**. Las llamadas nativas skills_list/skill_view de Hermes cargan el índice y las referencias de layout, audio y captions correctamente.
- Build real de Hermes con Remotion 4.0.529, React 19.3.0, Chrome Headless Shell y Edge TTS 7.2.8. No servicio adicional. Runner con H.264, 30 fps, canvas y tiempo impuestos, límite de 1 render por contenedor y concurrencia configurable 1–4, default 2. La salida se reemplaza solo si el render termina; bundle temporal eliminado al terminar.
- `docker compose exec -T hermes node --test /opt/quark-renderer/render-video.test.mjs`: **2 pruebas aprobadas**, duración/dimensiones/concurrencia inválidas y fuentes fuera del workspace rechazadas.
- Harness: crear `/workspace/hermes/remotion-runtime-tests` con grupo 10000 y modo 2770, luego `docker compose run --rm --no-deps --entrypoint node --user 10000:10000 -v ./tests:/opt/quark-tests:ro hermes /opt/quark-tests/remotion-smoke.mjs`: **7 casos aprobados**: dimensiones/duración, imagen local, audio, revisión del mismo archivo, vista de un fotograma, conservar el MP4 anterior ante error y rechazo de symlink fuera del workspace. Dos videos de **5,000 s de pista visual**, 320×320 y audio; duración de contenedor 5,056 s por padding AAC, dentro de 0,1 s. Renders **12,07 s y 12,11 s**, PNG **7,49 s** en esta PC local, no un benchmark del i3 del servidor. Sin LLM ni costo de tokens. Se inspeccionó la vista PNG; se omitió la cache de webpack para que el usuario 10000 no necesite escribir en dependencias de la imagen.
- Edge TTS real en Docker con voz es-AR-ElenaNeural: **5,976 s** de audio y SRT de 123 bytes. Usa red, sin clave adicional. El audio del harness de video es un tono de prueba, no una evaluación de la voz final.
- Reversión: quitar renderer/render-video*, sus paquetes npm y descarga de Chrome Headless Shell, skill/montaje Remotion, variable de concurrencia y Edge TTS de Hermes; reconstruir Hermes. El renderer estático Playwright, Manim, MPT, SVG+PNG y datos existentes permanecen.


## Selección de Remotion desde el chat

- `video_mode=motion` es aditivo y se conserva por conversación. Diseño animado y fotos originales usan Hermes/Remotion; explicación visual usa Hermes/Manim Community; escenas reales usan MPT. Sin dirección explícita ni delegación, el chat ofrece solo las opciones pertinentes, sin nombres técnicos. «Animado» solo no distingue entre explicación y diseño; una pregunta resuelve esa ambigüedad. Revisiones pueden cambiar la dirección explícitamente, y los modos históricos conservan su interpretación.
- SYSTEM, quark-marketing y el contexto privado reciben instrucciones acordes al motor seleccionado. Se reutiliza quark-narration únicamente si se solicita voz; texto exacto, dimensiones, originales, música y validación de archivos siguen vigentes. No se cambió el contrato de imágenes SVG+PNG ni Instagram.
- En el ensayo real, DeepSeek devolvió `palette=custom, colors=crema y bordó`, que disparaba el fallback del formulario y volvía a preguntar subject. El esquema ahora exige HEX al planificador y normaliza una lista acotada de nombres comunes; valores desconocidos o instrucciones siguen rechazados. Se conservan tema, texto, duración y dirección ya aportados. Pruebas de esa validación incluidas.
- `docker compose run --rm --no-deps -v ./tests:/app/tests:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q tests`: **146 pruebas aprobadas**, una advertencia existente de Starlette, **20,64 s**. Incluye elección inline, decisión ambigua, rechazo del desvío a stock, cambios de dirección, contexto con/sin narración y validación de paletas.
- Harness real de API: POST /api/projects y POST /api/projects/<id>/runs con un reel para la cafetería ficticia Pausa, diseño animado, 8 segundos, 9:16, sin voz/música, texto exacto y crema/bordó. Proyecto `23c6db3d90d444c4adb31f2c7815882c`: run **done**, un MP4 adjunto al chat, **8,000000 s**, **1080×1920**, sin pista de audio, fuente Video.tsx y plan/caption conservados. Se inspeccionaron fotogramas de apertura, desarrollo, transición y cierre; archivos de ensayo en el volumen y copias locales ignoradas bajo .tmp. La respuesta no expuso rutas ni herramientas. No se publicó en Instagram.
- Registro agent_usage de ese ensayo: **862.187 tokens de entrada**, de ellos **829.952 de caché**, **24.785 de salida**, costo **estimado US$0,02219611**, **334,002 s** de generación. La evaluación inicial del pedido se registra aparte en aux_usage. Es una sola muestra, no un promedio ni costo total de operación. Incluye múltiples revisiones de fotogramas; no demuestra baja latencia en el i3 ni calidad uniforme para otros pedidos. El render local no cobra tokens, pero hay costo de CPU/almacenamiento.
- Reversión de esta unidad: revertir motion en brief/shorts y sus instrucciones específicas en agent/SYSTEM/quark-marketing, pruebas y documentación de selección; la paleta normalizada puede conservarse independientemente. Los registros JSON viejos, conversaciones y exportaciones no se eliminan. Restaurar el contexto anterior de una nueva producción si queda un modo motion que el backend anterior no reconoce. El runtime y la skill del primer commit siguen utilizables por terminal dentro de Hermes.
## 2026-09-26 — Elección de voz independiente del tipo de video

- Cada video nuevo sin una decisión explícita pregunta narration; clips ya no activa voz automáticamente. Confirmar sin contestar esa pregunta devuelve 422. Las revisiones conservan la elección y distinguen sin voz en off de con voz en off. Imágenes y carruseles no preguntan voz.
- Suite de la imagen reconstruida: **170 pruebas aprobadas**, una advertencia existente de Starlette, **26,82 s**. Comando: `docker compose run --rm --no-deps -v ./tests:/app/tests:ro -e DATA_DIR=/tmp/quark-tests -e PYTHONPATH=/app studio pytest -q --tb=short tests`. Incluye los cuatro tipos de video, respuesta inline, persistencia, rechazo de confirmación prematura, pedido explícito y revisión. La guía montada describe Edge TTS para Hermes/Manim y Hermes/Remotion.
- API recreada con Compose tras comprobar cero tareas activas. Sin cambios de esquema SQL ni render adicional con LLM para estas pruebas. La síntesis Edge TTS y su montaje real ya se verificaron en la unidad anterior; esta suite valida la selección y el contexto, no la calidad de cada video.
- Reversión: revertir la elección y validación de narration en brief/agent, las instrucciones SYSTEM/quark-narration, pruebas y BRIEF.md; reconstruir studio. No borrar conversaciones ni exportaciones.

