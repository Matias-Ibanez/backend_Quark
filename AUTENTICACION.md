# Acceder a QUARK con la cuenta admin

QUARK tiene una única cuenta `admin`, sin registro público ni contraseña predeterminada. Antes de configurarla, la API y los archivos permanecen cerrados. El frontend muestra `/login`; cada profesor puede iniciar una sesión independiente con las mismas credenciales. Todos comparten conversaciones y recursos: no son cuentas personales.

El workflow de [DEPLOY_GITHUB.md](DEPLOY_GITHUB.md) inicializa la cuenta con `QUARK_ADMIN_PASSWORD` de GitHub Secrets por entrada estándar, solo cuando todavía no existe. No rota la contraseña en cada actualización. `PUBLIC_API_ORIGIN` permite un hostname propio de API para Vercel + túnel; `PUBLIC_APP_ORIGIN` sigue siendo el único origen autorizado del navegador.

## Crear o cambiar la contraseña

Desde el repositorio del backend, con Docker disponible:

```bash
docker compose build studio
docker compose run --rm --no-deps -it studio python -m backend.auth configure
```

El comando pide la contraseña dos veces sin mostrarla ni guardarla en `.env`. Se aceptan 12–128 caracteres; preferí una frase larga y única o una contraseña aleatoria de tu gestor. Ejecutarlo otra vez cambia la contraseña y revoca todas las sesiones. Actualizá también el frontend: ambos repositorios necesitan la versión que incluye el login.

Para probar localmente, iniciá el backend y el frontend como de costumbre, abrí `http://localhost:8010/chat` e ingresá como `admin`. Para salir, usá **Salir** en la cabecera. En desarrollo Next.js también admite `http://localhost:3000`.

Si necesitás cerrar todas las sesiones sin cambiar la contraseña:

```bash
docker compose run --rm --no-deps studio python -m backend.auth revoke
```

No hay recuperación por email ni restablecimiento público; el responsable usa estos comandos con acceso al servidor. No pases contraseñas como argumentos, no las pegues en el chat ni las subas a Git.

## Sesiones y protección

- Argon2id protege la contraseña, con sal aleatoria, 64 MiB y tres iteraciones. La verificación tiene un máximo de dos ejecuciones simultáneas.
- Cada ingreso genera un token aleatorio de 256 bits. Solo su hash se guarda en el servidor. La cookie es `HttpOnly`, `SameSite=Strict` y tiene `Path=/`, sin `Domain`; no hay tokens de acceso en localStorage.
- La sesión vence a las ocho horas o tras 30 minutos de inactividad. Consultas del chat cuentan como actividad. Salir revoca la sesión actual; cambiar la contraseña o usar `revoke` revoca todas. Reiniciar conserva las sesiones vigentes.
- Una pre-sesión de diez minutos protege el login. Cada operación que cambia datos requiere el token CSRF vinculado a la sesión. Se validan además Origin, Host y solicitudes entre sitios.
- El login admite diez intentos por dirección de conexión y cuarenta globales en quince minutos. Se cuentan también los ingresos correctos; los límites sobreviven a reinicios. No se confía en `X-Forwarded-For`: detrás de Next.js los profesores pueden compartir el mismo límite. Esperá el intervalo si lo alcanzan; `configure` permite recuperarse administrativamente.
- Conversaciones, costos, ajustes, subidas, descargas, medios y documentación de API requieren sesión. Los medios mantienen soporte Range para video y sandbox para SVG. Las respuestas privadas no se cachean.
- Solo quedan públicos el estado mínimo `/api/health`, el estado/login de autenticación y el webhook exacto de Instagram. Ese webhook conserva sus verificaciones de token/firma y rechaza solicitudes sin sus propios secretos; no habilita otras rutas de Instagram.
- Hay hasta 32 sesiones autenticadas y 256 pre-sesiones; se retiran las más antiguas al alcanzar el límite. WebSockets quedan cerrados porque el chat actual usa HTTP y polling.

## Almacenamiento y HTTPS

Compose guarda credenciales y sesiones en `studio-auth:/auth`, separado de `studio-data` y sin montarlo en Hermes. No agregues este volumen al agente. Respaldalo de forma privada junto con los datos si querés conservar el acceso; restaurar una copia puede restaurar sesiones antiguas, así que usá `revoke` después. Fuera de Docker se usa `.auth/`, excluido de Git y del build.

Al configurar más adelante el servidor, `PUBLIC_APP_ORIGIN` debe ser el origen HTTPS exacto. Activa cookies `Secure` con prefijo `__Host-` y rechaza orígenes HTTP o con rutas. El frontend y la API deben aparecer bajo el mismo origen. No publiques el puerto de Hermes ni abras directamente la API. TLS y la configuración del proxy se verificarán durante el despliegue; el login no reemplaza esas condiciones.

Referencias: [sesiones de OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [almacenamiento de contraseñas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) y [protección CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

La publicación externa de Instagram necesitará URLs de medios firmadas y con vencimiento cuando se retome esa integración: Meta no tiene la cookie de admin y no puede descargar ahora los medios privados. Las vistas PNG y descargas SVG siguen disponibles dentro de la sesión.
