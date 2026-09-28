# QUARK · backend

El acceso usa una única cuenta `admin` con sesiones privadas y revocables. Antes de usar el chat, configurá su contraseña siguiendo [AUTENTICACION.md](AUTENTICACION.md). No existe una contraseña predeterminada ni registro público; el frontend y este backend deben actualizarse juntos.

Este repositorio contiene la API, Hermes, las herramientas multimedia y los datos persistentes de QUARK. La interfaz vive en [landing-quark](https://github.com/Matias-Ibanez/landing-quark). DeepSeek aporta el modelo; las publicaciones estáticas se crean como SVG vectorial editable y Playwright/Chromium genera una vista PNG. Remotion, Manim y FFmpeg producen videos, y rembg separa sujetos de fotos subidas. Todo corre sin GPU dedicada y sin generación de fotografías por difusión. Una foto incorporada en un SVG sigue siendo raster; el texto y las formas son vectores.

Para desplegar automáticamente con el runner de la organización en otra LXC y Docker remoto, seguí [DEPLOY_GITHUB.md](DEPLOY_GITHUB.md). El workflow de `main` conserva volúmenes, instala skills desde las imágenes e inicializa admin solo una vez. Requiere configurar los Secrets y Variables de GitHub antes del primer despliegue.

## Iniciar el backend

Necesitás Docker Desktop o Docker Engine con Compose, y una clave de DeepSeek con saldo. Desde este repositorio:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux/macOS
cp .env.example .env
```

Completá `DEEPSEEK_API_KEY` en `.env`. Para crear shorts automáticos agregá una clave gratuita `PEXELS_API_KEY` obtenida en [Pexels API](https://www.pexels.com/api/). Luego iniciá los servicios:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8011/api/health
```

La respuesta debe incluir `"status":"ok"`. `studio` publica la API solo en `127.0.0.1:8011`; Hermes permanece en la red privada de Docker. `studio-data` conserva proyectos, mensajes y medios; `hermes-data` conserva las sesiones y configuración del agente. El primer build de Hermes puede tardar varios minutos y ocupar varios GB por Manim, LaTeX y Chromium.

En el chat, cada publicación estática se entrega como SVG escalable. El backend guarda también una vista PNG para la galería y para la futura publicación en Instagram. Las skills editoriales, de producto y tipográficas viven en `hermes/skills/` y se montan automáticamente con Compose.

También podés adjuntar PDF de hasta 30 MB y 60 páginas. La imagen de la API incluye Poppler para texto y portada y Tesseract con español/inglés para páginas escaneadas. El original se conserva, junto con texto extraído y una vista de la primera página. La skill `quark-documents`, montada automáticamente en Hermes, hace leer ese texto antes de escribir la pieza y trata el documento como datos, nunca como instrucciones. Hermes puede consultar todo el texto disponible; los videos con clips reciben extractos parciales de los documentos, identificados como tales.

La extracción admite hasta 120.000 caracteres y aplica OCR a las primeras 12 páginas que lo necesiten, incluso en documentos mixtos. La interfaz avisa si la lectura es parcial o no se pudo reconocer texto. El OCR puede equivocarse en nombres, cifras y fórmulas; no sustituye revisar el material. No se admite PDF con contraseña.

Si en el brief elegiste agregar música después, QUARK lo propone al terminar el video. Respondé **Sí** y buscá una canción por nombre o adjuntá un archivo MP3, WAV, OGG o M4A. Elegí y escuchá el tramo, indicá dónde empieza en el video y pulsá **Aplicar al último video**. También podés escribir **agregar música** en una conversación con un video anterior. La búsqueda usa `yt-dlp` y la importación usa `ytmdl` dentro del contenedor; ambas dependen de que YouTube esté accesible. La selección queda guardada para los próximos videos de esa conversación y mantiene la voz original. Para publicar el resultado fuera de la defensa, verificá que tengas permiso para usar la canción.

Para crear un short, escribí `Creá un short automático sobre café de especialidad para quienes empiezan`. Si no está clara la dirección visual, QUARK pregunta si preferís escenas reales, diseño animado o una explicación visual; también puede usar los originales aportados. La dirección con clips usa MoneyPrinterTurbo para guion en español, clips de Pexels, voz, subtítulos y un MP4; el diseño animado y el montaje con originales usan Remotion a través de Hermes; las explicaciones con gráficos y demostraciones usan Manim Community. Los shorts son verticales por defecto o respetan el formato confirmado. Respondé las preguntas necesarias y confirmá cuando se solicite. La música seleccionada en la conversación se agrega automáticamente. Pexels se configura una sola vez en el servidor; sin esa clave, QUARK muestra un error claro antes de gastar tokens. La imagen oficial de MoneyPrinterTurbo está fijada a la versión 1.3.7 y solo se comunica con la API por la red privada de Docker. Sus datos viven en `shorts-data`.

Los videos con voz usan [quark-narration](hermes/skills/quark-narration/SKILL.md), una adaptación de la skill de guion de GTM Agents: una idea, gancho concreto, desarrollo con hechos confirmados, frases pensadas para escucharse y un cierre acorde al objetivo. Hermes recibe la guía al generar videos narrados; MoneyPrinterTurbo recibe sus mismas reglas de escritura mediante `video_script_prompt`, acotado a su límite de 2.000 caracteres. El guion apunta inicialmente a unas dos palabras por segundo, pero la duración real depende de la voz y se valida sobre el video. El texto exacto aportado se conserva. No agrega otro proveedor ni una llamada adicional al modelo; sí aumenta algo el contexto de esa llamada. Videos sin voz e imágenes no reciben la guía completa de locución.

Para animaciones, Hermes carga [manimce-best-practices](hermes/skills/manimce-best-practices/SKILL.md), del repositorio [adithya-s-k/manim_skill](https://github.com/adithya-s-k/manim_skill). Compose monta automáticamente la skill completa, con guías de composición, texto, transiciones, ritmo, cámaras y gráficos, ejemplos y plantillas. La revisión de origen y modificaciones están en [UPSTREAM.md](hermes/skills/manimce-best-practices/UPSTREAM.md), con licencia MIT conservada. Su perfil QUARK usa Manim Community 0.20.1 y Cairo por CPU, respeta las dimensiones y la marca y evita abrir ventanas de reproducción. Se combina con quark-narration cuando hay voz; el modelo consulta solo las referencias pertinentes. Las rutas de clips e imágenes estáticas se conservan.

Para motion graphics, Hermes carga [remotion-best-practices](hermes/skills/remotion-best-practices/SKILL.md), el paquete oficial de [remotion-dev/skills](https://github.com/remotion-dev/skills), fijado a una revisión junto con Remotion 4.0.529 y React 19.3.0. Incluye referencias de diseño para video, tipografía, animación por fotogramas, secuencias, transiciones, fotos, audio y subtítulos. Su perfil QUARK evita instalaciones por chat, Studio, 3D y servicios pagos adicionales. La procedencia está en [UPSTREAM.md](hermes/skills/remotion-best-practices/UPSTREAM.md).

El runtime está preinstalado en Hermes, con Chrome Headless Shell. El agente escribe un componente `Video.tsx` y usa `render-video.mjs` para inspeccionar fotogramas y exportar un MP4 completo. El renderizador impone dimensiones, duración y 30 fps, conserva el resultado anterior si falla una revisión y permite un solo render simultáneo dentro del contenedor. `QUARK_REMOTION_CONCURRENCY` tiene un valor predeterminado de 2 y acepta 1–4; aumentarlo no garantiza más velocidad. Mantiene el límite de 6 GB y 4 CPU de Hermes. No necesita otra clave ni otro servicio. La locución opcional usa Edge TTS y requiere acceso a Internet; el montaje se renderiza localmente. La selección de música sigue aplicándose al MP4 desde el backend.

Remotion tiene [su propia licencia](hermes/renderer/REMOTION-LICENSE.md): permite el prototipo de evaluación y uso gratuito para individuos/equipos elegibles, y exige licencia de empresa fuera de esas condiciones. No se presenta como MIT.

En una PC de 16 GB, Hermes tiene un límite de 6 GB, MoneyPrinterTurbo de 4 GB y la API de 1,5 GB; el frontend separado tiene 1 GB. Son techos, no memoria reservada ni garantía de render más veloz. El generador de shorts usa 4 hilos y ambos motores de video pueden usar hasta 4 CPU cada uno; evitá renderizar con los dos motores simultáneamente en una CPU de 4 núcleos. `/api/costs` usa un delta aproximado del saldo DeepSeek para shorts cuando el proveedor lo informa; si todavía no se refleja el cobro, la ejecución queda marcada sin precio. CPU, red y almacenamiento no están incluidos.

## Iniciar también la interfaz

Antes de generar una pieza nueva, el agente evalúa lo que ya diste, los adjuntos y el contexto del chat. Si falta información, pregunta una decisión por vez dentro de la conversación; podés tocar una opción o escribir la respuesta en el mismo cuadro de mensajes. Si alcanza, produce directamente. No hace falta elegir una función de marketing. [BRIEF.md](BRIEF.md) detalla las preguntas, validación y entrega de carruseles.

QUARK también explica quién es, sus capacidades, el recorrido de trabajo y cómo empezar. Las preguntas frecuentes sobre el producto reciben orientación inmediata sin abrir un brief ni consumir tokens; la misma referencia de capacidades se incluye en el contexto del modelo. El acompañamiento se limita a marketing y comunicación de marca. No promete publicación o atención automática en Instagram desde el chat, fotografías nuevas ni resultados comerciales garantizados. Si una presentación viene acompañada de un pedido de producción, se conserva el pedido.

Cloná [landing-quark](https://github.com/Matias-Ibanez/landing-quark) en otra carpeta. Con el backend ya iniciado, ejecutá allí:

```bash
docker compose up -d --build
```

Abrí `http://localhost:8010/chat`. Ambos Compose comparten la red Docker `quark-shared`: el frontend envía las rutas `/api`, `/media`, `/fonts` y `/webhooks` a `studio` sin exponer Hermes. Para desarrollo sin Docker en el frontend, ejecutá `npm ci` y `npm run dev` desde `landing-quark`; su proxy apunta a `127.0.0.1:8011` y el chat queda en `http://localhost:3000/chat`.

Si el puerto 8011 está ocupado, cambiá `STUDIO_PORT` en el `.env` del backend y `QUARK_API_URL` al iniciar el frontend local. Si cambiás 8010, definí el mismo `FRONTEND_PORT` en los dos despliegues.

## Operación y despliegue

```bash
docker compose logs -f studio hermes  # Actividad del backend
docker compose up -d --build          # Actualización
docker compose stop                  # Apagar sin borrar datos
```

No uses `docker compose down -v` si querés conservar conversaciones y medios. `GET /api/costs` muestra costos **estimados** por ejecución y `GET /api/deepseek/balance` consulta el saldo informado por DeepSeek. Instagram queda como módulo separado para configurar más adelante.

Para instalar **ambos repositorios** en un servidor con TLS, seguí [DESPLIEGUE.md](DESPLIEGUE.md). [ARQUITECTURA.md](ARQUITECTURA.md) describe el flujo interno y [VERIFICATION.md](VERIFICATION.md) registra las comprobaciones. Las claves reales, la base de datos y los medios generados están excluidos de Git; rotá las claves que hayas compartido antes de desplegar.

## Render de publicaciones en CPU

El renderizador estático mantiene SVG descargable y PNG de 1080 px, sin GPU. Para un carrusel puede procesar hasta diez láminas con un solo Chromium, de forma secuencial para no saturar el i3. El agente usa `node /opt/quark-renderer/render.mjs --batch /workspace/hermes/PROYECTO/render-jobs.json`; el archivo es una lista de objetos con `source`, `output`, `width` y `height`. El comando individual anterior sigue funcionando.

Cada lámina mantiene una página aislada, bloqueo de recursos remotos y controles de dimensiones/recortes. Una salida se reemplaza solo después de un render válido. El backend publica un carrusel únicamente si todas sus láminas están completas. La salida del comando incluye segundos por lámina y tiempo total; no se aumentan RAM ni CPU de Compose para esta mejora.

El renderer comprueba todos los textos SVG, aunque no tengan una etiqueta de revisión: rechaza textos fuera del lienzo o con menos de 3% de margen en un borde. El agente debe ajustar la composición y repetir el render. Las figuras decorativas pueden llegar al borde; los textos en fotos o trazados requieren revisión visual.

Para posts y carruseles, `QUARK_POST_REASONING=off` es el valor predeterminado: DeepSeek usa sus herramientas sin razonamiento extendido. Las guías de estilo, el texto confirmado, la revisión visual y la resolución final permanecen. Los videos y la conversación general conservan la configuración de Hermes. Si un diseño complejo necesita el comportamiento anterior, cambiá a `QUARK_POST_REASONING=on` en `.env` y ejecutá `docker compose up -d studio`; no hace falta reconstruir las imágenes.

El flujo de publicaciones utiliza las guías ya incluidas en el contexto, consulta una dirección visual y renderiza directamente la vista final. Si el SVG no cambia durante la revisión, se entrega ese mismo PNG; si necesita correcciones, se vuelve a renderizar. La entrega conserva SVG editable y PNG. Más RAM o hilos de CPU no acelera las respuestas del proveedor; los tiempos de producción y tokens siguen registrados en `/api/costs` y en logs `agent_usage`.

Si elegiste texto exacto, la API deja una política de texto en el proyecto. El finalizador SVG rechaza frases añadidas o placeholders no respaldados, y el agente debe corregirlos antes de renderizar; el backend repite el control antes de entregar. Se permiten saltos de línea y etiquetas cortas de marca/rubro presentes en el contexto del usuario. Este control actúa sobre texto nativo SVG; la revisión visual sigue siendo necesaria para legibilidad, texto en fotos y elementos trazados.

Para revisar Remotion, el runner admite `node /opt/quark-renderer/render-video.mjs --preview SOURCE.tsx REVIEW.png WIDTH HEIGHT SECONDS [FRAMES]`. Produce una lámina numerada de seis fotogramas con un solo bundle y navegador, de forma secuencial. Los fotogramas se reducen a 540 px de ancho como máximo, conservando la composición y duración originales. FRAMES opcional es una lista de 4–6 números separados por comas, dentro de la línea de tiempo a 30 fps. Los comandos individuales PNG/MP4 siguen disponibles y la exportación final conserva su resolución.

La generación de diseño animado y videos con fotos propias usa un flujo controlado por la API: Hermes prepara las fuentes, la aplicación genera una lámina, Hermes la revisa y solo se permite una ronda de correcciones con una segunda revisión. Si quedan defectos, conserva las fuentes y devuelve un error concreto; no publica un borrador. Se comprueba la ejecución de la herramienta visual, la misma versión del código revisado, duración, dimensiones y audio cuando se pidió voz. El MP4 completo se renderiza una vez tras la aprobación.

Las etapas restringen las herramientas nativas de Hermes: creación hasta 16 turnos, corrección hasta 8, revisión hasta 3 y solo visión. El puente privado autenticado `/quark/video/render` ejecuta el renderer local en Hermes; no es una herramienta nueva que deba usar el modelo, no necesita puerto expuesto ni otra clave. Tokens de todas las etapas se suman al run, incluso si una etapa posterior falla; los tiempos de render aparecen como `motion_stage` en logs. Manim y el servicio de clips conservan sus rutas actuales.
