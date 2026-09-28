FROM nousresearch/hermes-agent@sha256:de97911af7b16a62e0f87c9e14f940df14da7e109ee0e823b821c228e9765832

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libcairo2-dev libpango1.0-dev pkg-config ffmpeg \
    fonts-dejavu-core fonts-liberation chromium texlive-latex-base texlive-latex-extra dvisvgm \
    && rm -rf /var/lib/apt/lists/*
RUN uv pip install --python /opt/hermes/.venv/bin/python 'manim==0.20.1' 'rembg[cpu]==2.0.67' 'edge-tts==7.2.8'
RUN ln -s /opt/hermes/.venv/bin/manim /usr/local/bin/manim
WORKDIR /opt/quark-renderer
COPY renderer/package.json renderer/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
RUN node --input-type=module -e "import {ensureBrowser} from '@remotion/renderer'; await ensureBrowser();"
COPY renderer/ ./
WORKDIR /opt/hermes
COPY patch_usage.py /tmp/patch_usage.py
COPY quark_video.py /opt/hermes/quark_video.py
COPY test_quark_video.py /opt/hermes/test_quark_video.py
RUN python /tmp/patch_usage.py && /opt/hermes/.venv/bin/python -m py_compile /opt/hermes/gateway/platforms/api_server.py
# CI seeds the private volume from these image-owned files; no remote host binds.
COPY config.yaml /opt/quark-deploy/config.yaml
COPY skills/ /opt/quark-deploy/skills/
COPY install_runtime.py /opt/quark-deploy/install_runtime.py
