"""Serialize GitHub deployment settings without evaluating or printing secrets."""
import os
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from urllib.parse import urlparse


def write_env(path, values):
    required = ('DEEPSEEK_API_KEY', 'PEXELS_API_KEY', 'HERMES_API_KEY',
                'SHORTS_API_KEY', 'PUBLIC_APP_ORIGIN', 'PUBLIC_API_ORIGIN')
    # Pasted provider keys/URLs often carry a trailing newline. Passwords stay exact.
    values = {**values, **{key: values.get(key, '').strip() for key in required}}
    for key in required:
        if not values.get(key):
            raise ValueError(f'Falta configurar {key} en GitHub Actions.')
    for key in ('HERMES_API_KEY', 'SHORTS_API_KEY'):
        if len(values[key]) < 32:
            raise ValueError(f'{key} requiere al menos 32 caracteres.')
    for key in ('PUBLIC_APP_ORIGIN', 'PUBLIC_API_ORIGIN'):
        parsed = urlparse(values[key])
        if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.params or parsed.query or parsed.fragment or parsed.username:
            raise ValueError(f'{key} debe ser un origen HTTPS sin ruta ni credenciales.')
        _ = parsed.port
    password = values.get('QUARK_ADMIN_PASSWORD', '')
    if not 12 <= len(password) <= 128 or '\n' in password or '\r' in password:
        raise ValueError('QUARK_ADMIN_PASSWORD requiere 12–128 caracteres, sin saltos de línea.')
    settings = {key: values[key] for key in required}
    settings.update({
        'STUDIO_PORT': values.get('STUDIO_PORT') or '8011',
        'STUDIO_BIND_IP': (values.get('STUDIO_BIND_IP') or '127.0.0.1').strip(),
        'FRONTEND_PORT': values.get('FRONTEND_PORT') or '8010',
        'QUARK_REMOTION_CONCURRENCY': values.get('QUARK_REMOTION_CONCURRENCY') or '4',
        'QUARK_POST_REASONING': values.get('QUARK_POST_REASONING') or 'off',
    })
    try:
        bind = IPv4Address(settings['STUDIO_BIND_IP'])
    except ValueError:
        raise ValueError('STUDIO_BIND_IP debe ser una dirección IPv4 privada o loopback.') from None
    networks = ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8')
    if not any(bind in IPv4Network(network) for network in networks):
        raise ValueError('STUDIO_BIND_IP solo admite IPv4 privada o loopback, no todas las interfaces.')
    for key in ('STUDIO_PORT', 'FRONTEND_PORT'):
        if not settings[key].isdigit() or not 1 <= int(settings[key]) <= 65535:
            raise ValueError(f'{key} debe ser un puerto válido.')
    if settings['QUARK_REMOTION_CONCURRENCY'] not in ('1', '2', '3', '4'):
        raise ValueError('QUARK_REMOTION_CONCURRENCY debe ser 1–4.')
    if settings['QUARK_POST_REASONING'] not in ('on', 'off'):
        raise ValueError('QUARK_POST_REASONING debe ser on u off.')
    lines = []
    for key, value in settings.items():
        if any(c in value for c in ('\n', '\r', '\0')):
            raise ValueError(f'{key} contiene caracteres no admitidos.')
        # Compose single quotes preserve $, # and shell-like text literally.
        escaped = value.replace("'", "\\'")
        lines.append(f"{key}='{escaped}'\n")
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
        os.chmod(path, 0o600)
        handle.writelines(lines)
    print('Configuración privada generada; valores omitidos.')


if __name__ == '__main__':
    try:
        write_env('.env', os.environ)
    except ValueError as error:
        raise SystemExit(str(error))
