"""Install bundled QUARK config/skills in Hermes' volume before gateway startup."""
import shutil
from pathlib import Path


def install(source=Path('/opt/quark-deploy'), target=Path('/opt/data')):
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source/'config.yaml', target/'config.yaml')
    (target/'config.yaml').chmod(0o644)
    for skill in (source/'skills').iterdir():
        if skill.is_dir():
            shutil.copytree(skill, target/'skills'/skill.name, dirs_exist_ok=True)
    print('Configuración y skills de QUARK instaladas; datos de Hermes conservados.')


if __name__ == '__main__':
    install()
