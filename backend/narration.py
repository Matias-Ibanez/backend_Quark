"""One voiceover guide shared by Hermes and MoneyPrinterTurbo."""
from pathlib import Path


_path = Path("/app/narration-skill.md")
if not _path.exists():
    _path = Path(__file__).parents[1] / "hermes" / "skills" / "quark-narration" / "SKILL.md"
SKILL = _path.read_text(encoding="utf-8")
SPOKEN_GUIDE = SKILL.split("## Guía del guion hablado\n", 1)[1].split("## Producción y revisión", 1)[0].strip()


def clip_script_prompt(seconds=None):
    timing = (f"Duración objetivo: {seconds} segundos, aproximadamente {seconds * 2} palabras con pausas."
              if seconds else "Duración objetivo: entre 25 y 40 segundos, aproximadamente 50 a 80 palabras con pausas.")
    prompt = timing + "\nAplicá esta guía al guion hablado de marketing en español:\n" + SPOKEN_GUIDE
    # MoneyPrinterTurbo 1.3.7 rejects longer prompts before invoking its LLM.
    if len(prompt) > 2000:
        raise ValueError("La guía de locución supera el límite del generador de clips")
    return prompt
