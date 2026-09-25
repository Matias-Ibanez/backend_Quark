# Levantar QUARK en un servidor con TLS

El despliegue usa el mismo `compose.yaml` que la PC local. Docker publica solo `web` en `127.0.0.1:8010`; `studio`, Hermes, SQLite y los archivos quedan detrás de la red interna. Tu proxy HTTPS existente debe dirigir el dominio a ese puerto y autenticar al operador: esta versión del prototipo es de **un solo usuario**.

## Preparación

Necesitás un servidor Linux con Docker Engine y Docker Compose, un dominio que ya llegue al servidor, certificado TLS en el proxy y una clave de DeepSeek. Reservá espacio para las imágenes Docker, los medios generados y los dos volúmenes persistentes. No se necesita GPU dedicada.

1. Cloná el repositorio y entrá en él:

   ```bash
   git clone "https://github.com/TU_USUARIO/TU_REPOSITORIO.git" quark-backend
   cd quark-backend
   cp .env.example .env
   ```

2. Editá `.env` con estos valores:

   ```dotenv
   DEEPSEEK_API_KEY=<CLAVE_NUEVA_DE_DEEPSEEK>
   HERMES_API_KEY=<SECRETO_ALEATORIO_LARGO>
   PUBLIC_APP_ORIGIN=https://quark.tu-dominio.com
   STUDIO_PORT=8010
   ```

   Generá `HERMES_API_KEY` con `openssl rand -hex 32`. `PUBLIC_APP_ORIGIN` debe coincidir exactamente con el origen del navegador y no llevar barra final. Dejá las variables de Instagram vacías hasta configurar esa integración. Conservá `.env` fuera de Git y con permisos restringidos (`chmod 600 .env`). Rotá las claves que hayas compartido antes.

3. Construí e iniciá el stack:

   ```bash
   docker compose up -d --build --remove-orphans
   docker compose ps
   curl -fsS http://127.0.0.1:8010/api/health
   ```

   La respuesta de salud debe incluir `"status":"ok"`. El primer build de Hermes tarda más porque instala Manim y LaTeX. Si el agente aún está arrancando, esperá unos segundos antes de enviar el primer pedido.

## Proxy HTTPS

Agregá estas directivas dentro del `server` HTTPS que ya tiene tu certificado. El ejemplo usa autenticación básica de Nginx; creá `/etc/nginx/quark.htpasswd` según la configuración de tu servidor.

```nginx
auth_basic "QUARK";
auth_basic_user_file /etc/nginx/quark.htpasswd;
client_max_body_size 30m;

location / {
    proxy_pass http://127.0.0.1:8010;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 600s;
}
```

Comprobá la sintaxis y recargá Nginx con `nginx -t` y el método habitual de tu distribución. Abrí `https://quark.tu-dominio.com/chat` y verificá que el chat, las subidas y las vistas previas funcionen desde ese dominio. TLS cifra la conexión; la autenticación impide que visitantes usen tu saldo de DeepSeek o vean los proyectos.

## Mantener y recuperar datos

```bash
docker compose logs -f studio hermes   # Diagnóstico y consumo estimado
docker compose up -d --build            # Actualizar código e imágenes
docker compose stop                    # Detener sin borrar datos
docker compose ps                      # Comprobar estado
```

Respaldá los volúmenes `studio-data` y `hermes-data` antes de migrar o actualizar el servidor. No uses `docker compose down -v`: elimina los volúmenes con proyectos, medios y sesiones. `/api/costs` registra estimaciones por tokens, mientras `/api/deepseek/balance` devuelve el saldo de la cuenta; pueden diferir por llamadas auxiliares y redondeos. La integración con Instagram sigue opcional y requiere sus propias credenciales.
