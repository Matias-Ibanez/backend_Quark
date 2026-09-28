FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DATA_DIR=/data
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl poppler-utils tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY backend ./backend
COPY hermes/SYSTEM.md ./SYSTEM.md
COPY hermes/skills/quark-marketing/SKILL.md ./marketing-skill.md
COPY hermes/skills/quark-static-post/SKILL.md ./static-post-skill.md
COPY hermes/skills/quark-narration/SKILL.md ./narration-skill.md
COPY hermes/skills/quark-narration/LICENSE ./narration-skill.LICENSE
COPY hermes/renderer/svg_artifact.py ./hermes/renderer/svg_artifact.py
RUN mkdir -p /data /auth && groupadd -g 10000 shared && useradd -m -u 10001 -G shared studio && chown -R studio:studio /data /auth /app && chmod 700 /auth
USER studio
EXPOSE 8000
CMD ["python", "-m", "backend.launch"]
