FROM nousresearch/hermes-agent@sha256:de97911af7b16a62e0f87c9e14f940df14da7e109ee0e823b821c228e9765832

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libcairo2-dev libpango1.0-dev pkg-config ffmpeg \
    fonts-dejavu-core fonts-liberation chromium texlive-latex-base texlive-latex-extra dvisvgm \
    && rm -rf /var/lib/apt/lists/*
RUN uv pip install --python /opt/hermes/.venv/bin/python 'manim==0.20.1' 'rembg[cpu]==2.0.67'
RUN ln -s /opt/hermes/.venv/bin/manim /usr/local/bin/manim
WORKDIR /opt/quark-renderer
COPY renderer/package.json renderer/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
COPY renderer/ ./
WORKDIR /opt/hermes
COPY patch_usage.py /tmp/patch_usage.py
RUN python /tmp/patch_usage.py && /opt/hermes/.venv/bin/python -m py_compile /opt/hermes/gateway/platforms/api_server.py
