# QUARK · backend y stack completo

Este repositorio contiene la API de QUARK, su agente Hermes y el frontend necesario para levantar el prototipo con un solo comando. El backend guarda conversaciones y piezas en SQLite y volúmenes Docker. DeepSeek aporta el modelo; Manim, FFmpeg, Pillow y rembg producen los medios en el servidor, sin GPU dedicada ni generación de fotografías por difusión.

## Levantarlo en tu PC

Necesitás Docker Desktop (Windows) o Docker Engine con el complemento Compose (Linux), y una clave de DeepSeek con saldo.

1. Copiá `.env.example` a `.env`:

   ```powershell
   # PowerShell
   Copy-Item .env.example .env
   ```

   ```bash
   # Linux/macOS
   cp .env.example .env
   ```

2. Editá `.env` y completá `DEEPSEEK_API_KEY`. Para uso local, los demás valores pueden quedar como están. `.env` está excluido de Git.
3. Desde la raíz del repositorio, iniciá todo:

   ```bash
   docker compose up -d --build
   docker compose ps
   ```

4. Abrí [http://localhost:8010/chat](http://localhost:8010/chat). La comprobación rápida es [http://localhost:8010/api/health](http://localhost:8010/api/health), que debe devolver `"status":"ok"`.

El primer build de Hermes instala Manim y LaTeX; puede tardar varios minutos. Si el puerto 8010 está ocupado, cambiá `STUDIO_PORT` en `.env` y abrí el nuevo puerto.

## Qué inicia Compose

| Servicio | Función | Acceso |
| --- | --- | --- |
| `web` | Interfaz y proxy de API/medios | `127.0.0.1:8010` por defecto |
| `studio` | FastAPI, SQLite, guardrails y exportaciones | Solo red Docker |
| `hermes` | Agente, skills y herramientas multimedia | Solo red Docker |

`studio-data` conserva proyectos, mensajes, recursos y exportaciones; `hermes-data` conserva la configuración y las sesiones del agente. Para iterar una pieza, seguí escribiendo en la misma conversación. QUARK adjunta al chat el único archivo final validado de cada pedido; no entrega escenas parciales ni rutas del contenedor.

## Operación habitual

```bash
docker compose logs -f studio hermes  # Ver actividad y errores
docker compose up -d --build          # Actualizar después de cambiar el código
docker compose stop                  # Apagar sin borrar proyectos
```

No uses `docker compose down -v` si querés conservar conversaciones y medios. `GET /api/costs` muestra costos **estimados** por ejecución; `GET /api/deepseek/balance` consulta el saldo informado por DeepSeek. Instagram está incluido como módulo separado para configurar más adelante.

## Subir este repositorio a GitHub

La clave real, la base de datos, los archivos generados y las dependencias están ignorados por Git. Rotá cualquier clave que hayas compartido anteriormente antes de publicar o desplegar el repositorio. Después de crear un repositorio **vacío** en GitHub, reemplazá `TU_USUARIO/TU_REPOSITORIO` por su dirección y subí esta rama:

```bash
git remote add origin "https://github.com/TU_USUARIO/TU_REPOSITORIO.git"
git push -u origin main
```

Para instalarlo en un servidor con TLS y autenticación, seguí [DESPLIEGUE.md](DESPLIEGUE.md). [ARQUITECTURA.md](ARQUITECTURA.md) describe el flujo interno y [VERIFICATION.md](VERIFICATION.md) registra cómo se verificó el prototipo.
