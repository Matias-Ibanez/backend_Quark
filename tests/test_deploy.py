import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from deploy.write_env import write_env
from hermes.install_runtime import install


def settings():
    return {
        'DEEPSEEK_API_KEY': 'dummy-key', 'PEXELS_API_KEY':'dummy-pexels',
        'HERMES_API_KEY':'H'*32, 'SHORTS_API_KEY':'S'*32,
        'PUBLIC_APP_ORIGIN':'https://quark.test', 'PUBLIC_API_ORIGIN':'https://api.quark.test',
        'QUARK_ADMIN_PASSWORD':'Only-a-test-password-2026!',
    }


@pytest.mark.parametrize('key,value', [
    ('DEEPSEEK_API_KEY',''), ('PUBLIC_APP_ORIGIN','http://quark.test'),
    ('PUBLIC_API_ORIGIN','https://api.quark.test/path'), ('HERMES_API_KEY','short'),
    ('QUARK_ADMIN_PASSWORD','short'), ('PEXELS_API_KEY','key\nINJECTED=value'),
    ('STUDIO_PORT','0'), ('QUARK_REMOTION_CONCURRENCY','5'),
])
def test_invalid_settings_fail_before_creating_file(tmp_path, key, value):
    values = {**settings(),key:value}
    target = tmp_path/'.env'
    with pytest.raises(ValueError):
        write_env(target,values)
    assert not target.exists()


def test_env_never_contains_admin_password_or_prints_secret(tmp_path, capsys):
    values = settings()
    target = tmp_path/'.env'
    write_env(target, values)
    assert values['QUARK_ADMIN_PASSWORD'] not in target.read_text()
    output = capsys.readouterr().out
    assert all(value not in output for value in values.values())
    if os.name != 'nt':
        assert target.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(not shutil.which('docker'), reason='Docker CLI needed; no daemon used')
def test_compose_reads_quoted_secrets_literally(tmp_path):
    values = {**settings(), 'DEEPSEEK_API_KEY': "test$HOME${ABC}#'\\path"}
    write_env(tmp_path/'.env', values)
    compose = tmp_path/'compose.yaml'
    compose.write_text('services:\n  probe:\n    image: alpine\n    env_file: .env\n    environment:\n      SECOND_COPY: ${DEEPSEEK_API_KEY}\n')
    result = subprocess.run(['docker','compose','--env-file',str(tmp_path/'.env'),'-f',str(compose),'config','--format','json'],capture_output=True,text=True,check=True,timeout=20)
    env = json.loads(result.stdout)['services']['probe']['environment']
    assert env['DEEPSEEK_API_KEY'] == env['SECOND_COPY']
    # config serialization escapes $ as $$; inspect interpolation inputs too.
    inputs = subprocess.run(['docker','compose','--env-file',str(tmp_path/'.env'),'-f',str(compose),'config','--environment'],capture_output=True,text=True,check=True,timeout=20)
    parsed = dict(line.split('=',1) for line in inputs.stdout.splitlines() if '=' in line)
    assert parsed['DEEPSEEK_API_KEY'] == values['DEEPSEEK_API_KEY']


def test_image_seed_preserves_data_and_installs_licenses(tmp_path):
    source, target = tmp_path/'image', tmp_path/'volume'
    (source/'skills'/'example').mkdir(parents=True)
    (source/'config.yaml').write_text('model: example')
    for name in ('SKILL.md','LICENSE.txt','UPSTREAM.md'):
        (source/'skills'/'example'/name).write_text(name)
    target.mkdir()
    (target/'sessions.sqlite').write_bytes(b'user-data')
    install(source,target)
    assert (target/'sessions.sqlite').read_bytes() == b'user-data'
    assert all((target/'skills'/'example'/name).read_text() == name for name in ('SKILL.md','LICENSE.txt','UPSTREAM.md'))
    (source/'config.yaml').write_text('model: updated')
    install(source,target)
    assert (target/'config.yaml').read_text() == 'model: updated'

