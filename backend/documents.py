"""Bounded local PDF extraction. Documents are data, never agent instructions."""
import json
import re
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException
from . import store

MAX_PAGES = 60
MAX_TEXT = 120_000
OCR_PAGES = 12


def process_pdf(raw: bytes, asset_id: str):
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(422, "El archivo no es un PDF válido.")
    path = store.DATA / "assets" / f"{asset_id}.pdf"
    path.write_bytes(raw)
    outputs = [path, path.with_suffix(".txt"), path.with_suffix(".json"), path.with_name(f"{asset_id}-preview.png")]
    try:
        info = subprocess.run(["pdfinfo", str(path)], capture_output=True, timeout=10)
        metadata = info.stdout.decode("utf-8", errors="replace")
        match = re.search(r"^Pages:\s*(\d+)", metadata, re.M)
        if info.returncode or not match or re.search(r"^Encrypted:\s*yes", metadata, re.M):
            raise ValueError("locked")
        pages = int(match[1])
        if not 1 <= pages <= MAX_PAGES:
            raise HTTPException(422, f"Subí un PDF de hasta {MAX_PAGES} páginas.")
        subprocess.run(["pdftoppm", "-f", "1", "-singlefile", "-scale-to", "800", "-png", str(path), str(path.with_name(f"{asset_id}-preview"))],
                       capture_output=True, check=True, timeout=20)
        # Write to a bounded temporary disk file instead of retaining untrusted stdout in RAM.
        with tempfile.TemporaryDirectory() as temp:
            extracted = Path(temp) / "text.txt"
            subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(path), str(extracted)],
                           capture_output=True, check=True, timeout=20)
            with extracted.open(encoding="utf-8", errors="replace") as stream:
                text = stream.read(MAX_TEXT + 1)
            truncated = len(text) > MAX_TEXT
            status = "ready"
            page_texts = text.split("\f")[:pages]
            # Mixed documents can contain both selectable text and scanned pages.
            # Never treat a digital cover as proof that the remaining pages were read.
            if not truncated:
                page_texts += [""] * (pages - len(page_texts))
                scans = [i for i, content in enumerate(page_texts) if not content.strip()]
                for index in scans[:OCR_PAGES]:
                    page = index + 1
                    prefix = Path(temp) / f"page-{page}"
                    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-scale-to", "1400", "-png", str(path), str(prefix)],
                                   capture_output=True, check=True, timeout=15)
                    result = subprocess.run(["tesseract", str(prefix.with_suffix(".png")), "stdout", "-l", "spa+eng"],
                                            capture_output=True, check=True, timeout=15)
                    page_texts[index] = result.stdout.decode("utf-8", errors="replace")[:12000]
                text = "\n".join(f"[Página {i + 1}]\n{content}" for i, content in enumerate(page_texts))
                status = "partial" if len(scans) > OCR_PAGES else "ocr" if scans else "ready"
                if not any(content.strip() for content in page_texts):
                    status = "empty"
            document = {"pages": pages, "textStatus": status, "textTruncated": truncated or len(text) > MAX_TEXT,
                        "previewUrl": f"/media/assets/{asset_id}-preview.png"}
            path.with_suffix(".txt").write_text(text[:MAX_TEXT], encoding="utf-8")
            path.with_suffix(".json").write_text(json.dumps(document), encoding="utf-8")
        return document
    except HTTPException:
        for output in outputs:
            output.unlink(missing_ok=True)
        raise
    except (OSError, ValueError, subprocess.SubprocessError):
        for output in outputs:
            output.unlink(missing_ok=True)
        raise HTTPException(422, "No pude leer ese PDF. Revisá que no tenga contraseña y probá exportarlo de nuevo.")


def context(asset, *, excerpt=False):
    item = {"name": asset["name"], "kind": asset["kind"], "path": "/workspace/assets/" + asset["filename"]}
    if asset["kind"] == "document":
        path = store.DATA / "assets" / asset["filename"]
        item.update(document=asset.get("document", {}), text_path="/workspace/assets/" + path.with_suffix(".txt").name)
        if excerpt and path.with_suffix(".txt").is_file():
            with path.with_suffix(".txt").open(encoding="utf-8") as stream:
                item["excerpt"] = stream.read(2500)
    return item
