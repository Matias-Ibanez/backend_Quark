# Levantar QUARK en un servidor con TLS

QUARK usa dos repositorios y dos despliegues Compose en el mismo servidor. [backend_Quark](https://github.com/Matias-Ibanez/backend_Quark) inicia `studio` y Hermes; [landing-quark](https://github.com/Matias-Ibanez/landing-quark) inicia Next.js. Comparten la red Docker `quark-shared`. El proxy HTTPS apunta al frontend en `127.0.0.1:8010`; la API solo escucha en `127.0.0.1:8011` y en la red compartida. El prototipo es de **un solo usuario** y necesita autenticación en el proxy.

## Preparación

Necesitás Docker Engine con Compose, un dominio con TLS en tu proxy y una clave de DeepSeek con saldo. Reservá espacio para las imágenes Docker, los medios generados y los dos volúmenes persistentes. No se necesita GPU dedicada.

```bash
git clone https://github.com/Matias-Ibanez/backend_Quark.git quark-backend
git clone https://github.com/Matias-Ibanez/landing-quark.git quark-frontend
cd quark-backend
cp .env.example .env
```

Editá `quark-backend/.env` con estos valores:

```dotenv
DEEPSEEK_API_KEY=<CLAVE_NUEVA_DE_DEEPSEEK>
HERMES_API_KEY=<SECRETO_ALEATORIO_LARGO>
PUBLIC_APP_ORIGIN=https://quark.tu-dominio.com
STUDIO_PORT=8011
FRONTEND_PORT=8010
```

Generá `HERMES_API_KEY` con `openssl rand -hex 32`. `PUBLIC_APP_ORIGIN` debe ser el origen exacto del navegador, sin barra final. Dejá Instagram sin configurar hasta que lo uses. Conservá `.env` fuera de Git y con permisos restringidos (`chmod 600 .env`). Rotá las claves compartidas anteriormente.

## Iniciar los dos repositorios

```bash
cd quark-backend
docker compose up -d --build
curl -fsS http://127.0.0.1:8011/api/health

cd ../quark-frontend
docker compose up -d --build
curl -fsS http://127.0.0.1:8010/api/health
```

Ambas comprobaciones deben devolver `"status":"ok"`. Iniciá primero el backend: crea la red `quark-shared` que utiliza el frontend. El primer build de Hermes instala Manim, LaTeX, Chromium y Playwright; puede tardar varios minutos y requiere espacio de disco adicional. Si el agente aún arranca, esperá antes de enviar el primer pedido.

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

Comprobá la sintaxis y recargá Nginx con `nginx -t` y el método habitual de tu distribución. Abrí `https://quark.tu-dominio.com/chat` y verificá el chat, las subidas y las vistas previas. No publiques el puerto de Hermes; el frontend accede al backend por la red Docker compartida.

## Mantener y recuperar datos

Desde cada repositorio, `docker compose up -d --build` actualiza su servicio; `docker compose logs -f` muestra los errores. En el backend, `docker compose stop` detiene `studio` y Hermes sin borrar los datos. Respaldá `studio-data` y `hermes-data` antes de migrar o actualizar. No uses `docker compose down -v`: elimina proyectos, medios y sesiones. Evitá `docker compose down` en el backend mientras el frontend siga conectado a `quark-shared`.

`/api/costs` registra estimaciones por tokens y `/api/deepseek/balance` devuelve el saldo informado por DeepSeek; pueden diferir por llamadas auxiliares y redondeos. Instagram sigue opcional y requiere credenciales propias.
