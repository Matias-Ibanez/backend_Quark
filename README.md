# QUARK · backend

Este repositorio contiene la API, Hermes, las herramientas multimedia y los datos persistentes de QUARK. La interfaz vive en [landing-quark](https://github.com/Matias-Ibanez/landing-quark). DeepSeek aporta el modelo; las publicaciones estáticas se crean como SVG vectorial editable y Playwright/Chromium genera una vista PNG. Manim y FFmpeg producen videos, y rembg separa sujetos de fotos subidas. Todo corre sin GPU dedicada y sin generación de fotografías por difusión. Una foto incorporada en un SVG sigue siendo raster; el texto y las formas son vectores.

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

Cuando QUARK termina un video, pregunta si querés agregar música. Respondé **Sí** y buscá una canción por nombre o adjuntá un archivo MP3, WAV, OGG o M4A. Elegí y escuchá el tramo, indicá dónde empieza en el video y pulsá **Aplicar al último video**. También podés escribir **agregar música** en una conversación con un video anterior. La búsqueda usa `yt-dlp` y la importación usa `ytmdl` dentro del contenedor; ambas dependen de que YouTube esté accesible. La selección queda guardada para los próximos videos de esa conversación y mantiene la voz original. Para publicar el resultado fuera de la defensa, verificá que tengas permiso para usar la canción.

Para crear un short, elegí **Short automático · solo tema** y escribí, por ejemplo, `Café de especialidad para quienes empiezan`. MoneyPrinterTurbo prepara guion breve en español, clips de Pexels, voz, subtítulos y un MP4 vertical. La música seleccionada en la conversación se agrega automáticamente. Pexels se configura una sola vez en el servidor; sin esa clave, QUARK muestra un error claro antes de gastar tokens. La imagen oficial de MoneyPrinterTurbo está fijada a la versión 1.3.7 y solo se comunica con la API por la red privada de Docker. Sus datos viven en `shorts-data`.

En una PC de 16 GB, Hermes tiene un límite de 6 GB, MoneyPrinterTurbo de 4 GB y la API de 1,5 GB; el frontend separado tiene 1 GB. Son techos, no memoria reservada ni garantía de render más veloz. El generador de shorts usa 4 hilos y ambos motores de video pueden usar hasta 4 CPU cada uno; evitá renderizar con los dos motores simultáneamente en una CPU de 4 núcleos. `/api/costs` usa un delta aproximado del saldo DeepSeek para shorts cuando el proveedor lo informa; si todavía no se refleja el cobro, la ejecución queda marcada sin precio. CPU, red y almacenamiento no están incluidos.

## Iniciar también la interfaz

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
