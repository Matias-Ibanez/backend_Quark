# Desplegar el backend con el runner de la organización

El workflow `.github/workflows/deploy.yml` despliega `main` en Docker remoto, por defecto `tcp://10.10.10.102:2375`. El runner puede estar en otra LXC. Solo despliega el backend: el frontend en Vercel se configura por separado. También podés ejecutarlo desde **Actions → Deploy QUARK backend to LXC → Run workflow**, seleccionando `main`.

## Configuración inicial en GitHub

En **Settings → Secrets and variables → Actions**, agregá estos **Secrets** en el repositorio o habilitá sus equivalentes de organización para este repo:

- `DEEPSEEK_API_KEY`: clave del modelo.
- `PEXELS_API_KEY`: clave de la biblioteca de clips para shorts.
- `HERMES_API_KEY`: secreto aleatorio de al menos 32 caracteres para API ↔ Hermes.
- `SHORTS_API_KEY`: otro secreto aleatorio de al menos 32 caracteres para API ↔ MoneyPrinterTurbo.
- `QUARK_ADMIN_PASSWORD`: contraseña inicial de `admin`, de 12–128 caracteres. No se escribe en `.env`, código ni argumentos del proceso.

Generá cada secreto de servicio por separado con `openssl rand -hex 32`. No reutilices las claves de proveedores como secretos internos. No hace falta Supabase ni ningún secret de Instagram para este despliegue.

Agregá estas **Variables**:

Las URLs `PUBLIC_APP_ORIGIN` y `PUBLIC_API_ORIGIN` también pueden estar en **Secrets**, si ya las guardaste allí. El workflow admite ambas ubicaciones; si existe una Variable no vacía con el mismo nombre, tiene prioridad. Los demás ajustes de esta lista se leen como Variables.

- `PUBLIC_APP_ORIGIN`: origen HTTPS final del frontend, por ejemplo `https://quark.tudominio.com`, sin barra final ni ruta.
- `PUBLIC_API_ORIGIN`: origen HTTPS del túnel del backend, por ejemplo `https://api.quark.tudominio.com`, sin barra final ni ruta. Autoriza ese hostname; el origen permitido del navegador sigue siendo exclusivamente el del frontend.
- `QUARK_DOCKER_HOST`: opcional; por defecto `tcp://10.10.10.102:2375`. Cambialo si la LXC destino es otra.
- `STUDIO_PORT`: opcional; por defecto `8011`, enlazado solo a `127.0.0.1` de la LXC Docker.
- `QUARK_REMOTION_CONCURRENCY`: opcional, `1`–`4`, por defecto `2` para el i3.
- `QUARK_POST_REASONING`: opcional, `off` u `on`, por defecto `off`.

El workflow valida todo antes de construir o modificar servicios. Si faltan secretos/orígenes, falla indicando sus nombres, sin imprimir valores. No incluye credenciales predeterminadas. **Agregar este workflow no configura automáticamente los Secrets de GitHub.**

Al copiar claves o URLs, se eliminan espacios y saltos de línea de los extremos. Un salto de línea dentro del valor se sigue rechazando. La contraseña admin se usa exactamente como fue guardada, sin recortarla.

## Requisitos del runner y la LXC Docker

El runner de organización debe admitir este repositorio y tener etiquetas `self-hosted` y `linux`, Bash, Python 3, Docker CLI y Docker Compose **2.24.4 o posterior**. Debe poder conectarse a la LXC Docker y descargar el checkout de GitHub. La LXC Docker requiere espacio para Manim, LaTeX, Chromium y los datos, y salida a Internet para descargar imágenes y contactar proveedores.

El endpoint Docker `2375` permite administrar el host sin autenticación TLS. Restringilo por firewall a la IP del runner en la red privada; no lo publiques en Internet ni mediante Cloudflare Tunnel. Si ya tenés un endpoint con TLS/contexto, adaptá la conexión del workflow antes de usarlo.

La API sigue cerrada sin sesión. El workflow no abre puertos de Hermes ni de MoneyPrinterTurbo, no modifica tus túneles y no administra otras aplicaciones del servidor. Usa el nombre de proyecto **`lienzo`** para conservar los volúmenes existentes; no lo cambies entre despliegues.

## Qué sucede al hacer push

1. Obtiene el código con checkout fijado a una revisión de v4, sin conservar credenciales Git.
2. Genera `.env` con permisos `600`, secretos tratados como texto literal y sin mostrar contenidos.
3. Valida Compose y la conexión Docker. Construye las tres imágenes de forma secuencial, mientras el stack anterior sigue activo.
4. Detiene Hermes e instala la configuración y las nueve skills desde su imagen en `hermes-data`. Conserva sesiones y otros datos del agente, incluidas las licencias y referencias upstream de las skills.
5. Inicializa `admin` por entrada estándar únicamente si no existe. **Actualizar un secret no cambia una contraseña existente ni cierra sesiones.** Para rotarla, usá el comando interactivo de AUTENTICACION.md.
6. Recrea los tres servicios y conserva `studio-data`, `studio-auth`, `hermes-data` y `shorts-data`.
7. Comprueba desde la red Docker la API, configuración de admin, rechazo del acceso anónimo, salud de Hermes, API de tareas de shorts y presencia de las skills. No genera contenido ni consume LLM. Espera hasta cinco minutos de arranque, más el tiempo de la última comprobación.
8. Borra `.env` del workspace del runner, incluso si falla. Los contenedores conservan las variables necesarias.

El job tiene un límite de **60 minutos** por el primer build pesado; las ejecuciones se serializan para que dos pushes no actualicen el mismo stack simultáneamente. Hay una interrupción al recrear servicios y una generación en curso puede cortarse: programá actualizaciones fuera de las demostraciones.

No ejecuta `down`, `down -v`, limpieza de imágenes ni `--remove-orphans`. Un fallo de build deja el stack previo en ejecución. Un fallo después de detener/recrear servicios requiere revisar y repetir el despliegue: **no hay rollback automático**.

## Archivos de producción y Docker remoto

El workflow combina `compose.yaml` con `compose.deploy.yaml`. El segundo reemplaza los bind mounts de Hermes y shorts: Docker remoto no puede montar archivos del checkout del runner. La imagen de Hermes incorpora configuración/skills y un instalador; la imagen derivada de MoneyPrinterTurbo incorpora su configurador. El Compose local conserva sus montajes habituales.

Para operar manualmente desde el runner, usá el mismo destino y los mismos archivos:

```bash
export DOCKER_HOST=tcp://10.10.10.102:2375
export COMPOSE_PROJECT_NAME=lienzo
export COMPOSE_FILE=compose.yaml:compose.deploy.yaml
docker compose ps
```

Después de un workflow, `.env` ya no existe en el runner. Para modificar o recrear servicios, regenerá la configuración privada o volvé a ejecutar el workflow; no uses el Compose local solo contra el Docker remoto. Para logs de producción, usá una configuración privada equivalente y `docker compose logs --tail=100 studio hermes shorts`; no copies logs con datos de usuarios o claves al repositorio.

## Conectar Cloudflare y Vercel después

Si `cloudflared` está instalado en la misma LXC Docker, apuntá el hostname de la API a `http://127.0.0.1:8011`. Si corre como contenedor, conectalo a la red `quark-shared` y apuntá a `http://studio:8000`. Si está en otra LXC, loopback no llega al backend: habrá que ajustar su conectividad antes de publicar el túnel. No asumas que `http://10.10.10.102:8011` es accesible, porque Compose publica solo en loopback.

En Vercel, importá el repo del frontend y definí `QUARK_API_URL=https://api.quark.tudominio.com` antes del build. Su dominio público debe coincidir exactamente con `PUBLIC_APP_ORIGIN`. Las rewrites mantienen `/api`, `/media`, `/fonts` y `/webhooks` bajo el origen del frontend. Conservá las respuestas privadas sin caché; no actives reglas de caché general para esas rutas en Cloudflare.

Después verificá el dominio real: login y logout, protección de API/medios sin cookie, subida de una imagen y un PDF, generación, reproducción y descarga. Las comprobaciones del workflow no validan por sí solas DNS, Cloudflare, cookies a través de Vercel ni límites de archivos del proxy. Esa prueba externa sigue pendiente.

Para cambiar o revocar credenciales en la LXC, ver [AUTENTICACION.md](AUTENTICACION.md). Para el despliegue manual de ambos repositorios en el mismo servidor, ver [DESPLIEGUE.md](DESPLIEGUE.md).
