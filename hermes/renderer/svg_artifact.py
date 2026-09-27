"""Finalize and validate self-contained SVG marketing artifacts."""

import base64
import binascii
import io
import re
import sys
import json
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image, UnidentifiedImageError

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ALLOWED_TAGS = {
    "svg", "g", "defs", "rect", "circle", "ellipse", "line", "polyline", "polygon", "path",
    "text", "tspan", "textPath", "linearGradient", "radialGradient", "stop", "clipPath",
    "mask", "pattern", "image", "symbol", "use", "filter", "feGaussianBlur", "feOffset",
    "feMerge", "feMergeNode", "feColorMatrix", "feComposite", "feFlood", "feBlend",
}
URL_REF = re.compile(r"url\(\s*['\"]?#[A-Za-z_][\w:.-]*['\"]?\s*\)")
DATA_IMAGE = re.compile(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)\Z", re.I)
MAX_SVG_BYTES = 25 * 1024 * 1024
MAX_IMAGE_BYTES = 12 * 1024 * 1024
ASSETS = Path("/workspace/assets")


class InvalidSVG(ValueError):
    pass


def _image_data(raw: bytes, kind: str) -> str:
    if len(raw) > MAX_IMAGE_BYTES:
        raise InvalidSVG("An embedded image is too large")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > 25_000_000 or image.format.lower() not in ("png", "jpeg", "webp"):
                raise InvalidSVG("Unsupported embedded image")
            actual = image.format.lower()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidSVG("Invalid embedded image") from exc
    if actual != kind:
        raise InvalidSVG("Embedded image MIME does not match its bytes")
    return f"data:image/{actual};base64,{base64.b64encode(raw).decode('ascii')}"


def _embed_local(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme == "file" and not parsed.netloc and not parsed.query and not parsed.fragment:
        filename = unquote(parsed.path)
    elif not parsed.scheme and value.startswith("/workspace/assets/"):
        filename = value
    else:
        raise InvalidSVG("Only uploaded local images are allowed")
    target = Path(filename).resolve()
    root = ASSETS.resolve()
    if root not in target.parents or not target.is_file():
        raise InvalidSVG("Image path must point to an uploaded asset")
    kind = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp"}.get(target.suffix.lower())
    if not kind:
        raise InvalidSVG("Unsupported image format")
    return _image_data(target.read_bytes(), kind)


def finalize_svg(raw: bytes, *, embed_local: bool = False) -> bytes:
    if len(raw) > MAX_SVG_BYTES or re.search(rb"<!DOCTYPE|<!ENTITY|<\?", raw, re.I):
        raise InvalidSVG("SVG contains unsupported XML or exceeds the size limit")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise InvalidSVG("SVG is not valid XML") from exc
    if root.tag != f"{{{SVG_NS}}}svg":
        raise InvalidSVG("Expected an SVG root element")
    for dimension in ("width", "height"):
        value = root.get(dimension, "")
        if not value.isdecimal() or not 320 <= int(value) <= 2160:
            raise InvalidSVG("SVG width and height must be 320–2160 pixels")
    if len(list(root.iter())) > 3000:
        raise InvalidSVG("SVG has too many elements")
    for element in root.iter():
        if not element.tag.startswith("{" + SVG_NS + "}") or element.tag.split("}", 1)[1] not in ALLOWED_TAGS:
            raise InvalidSVG("Unsupported SVG element")
        tag = element.tag.split("}", 1)[1]
        for key, value in list(element.attrib.items()):
            name = key.split("}", 1)[-1]
            if name.lower().startswith("on") or name == "style" or key.startswith("{") and not key.startswith("{" + XLINK_NS + "}"):
                raise InvalidSVG("Unsafe SVG attribute")
            if name == "href":
                if tag == "image":
                    match = DATA_IMAGE.fullmatch(value)
                    if match:
                        try:
                            raw_image = base64.b64decode(match.group(2), validate=True)
                        except binascii.Error as exc:
                            raise InvalidSVG("Invalid embedded image encoding") from exc
                        element.set(key, _image_data(raw_image, match.group(1).lower()))
                    elif embed_local:
                        element.set(key, _embed_local(value))
                    else:
                        raise InvalidSVG("SVG images must be embedded")
                elif not re.fullmatch(r"#[A-Za-z_][\w:.-]*", value):
                    raise InvalidSVG("External SVG references are not allowed")
            elif "url(" in value.lower():
                if not URL_REF.fullmatch(value.strip()):
                    raise InvalidSVG("External SVG resources are not allowed")
            elif re.search(r"(?:javascript|https?|file|data):", value, re.I):
                raise InvalidSVG("External or executable SVG attribute")
    result = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    if len(result) > MAX_SVG_BYTES:
        raise InvalidSVG("Final SVG exceeds the size limit")
    return result


def unexpected_copy(svg, exact_text, provided_text):
    """Reject added visible phrases when copy is exact; allow explicit short brand labels."""
    def words(value):
        value = unicodedata.normalize("NFKD", value.casefold())
        value = "".join(c for c in value if not unicodedata.combining(c))
        return " ".join(re.findall(r"\w+", value))
    quoted = re.findall(r"«([^»]+)»", exact_text)
    expected = [words(text) for text in (quoted or [exact_text])]
    supplied = " " + words(provided_text) + " "
    issues = []
    for node in ET.fromstring(svg).iter("{" + SVG_NS + "}text"):
        text = " ".join(node.itertext()).strip()
        normalized = words(text)
        if not normalized:
            continue
        if any(" " + normalized + " " in " " + allowed + " " for allowed in expected):
            continue
        if len(normalized.split()) <= 4 and " " + normalized + " " in supplied:
            continue
        issues.append(text[:200])
    return issues


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit("Usage: python svg_artifact.py SOURCE.svg FINAL.svg [COPY_POLICY.json]")
    source, output = (Path(item).resolve() for item in sys.argv[1:3])
    workspace = Path("/workspace/hermes").resolve()
    if workspace not in source.parents or workspace not in output.parents:
        raise SystemExit("Source and output must be inside /workspace/hermes")
    if source.suffix != ".svg" or output.suffix != ".svg":
        raise SystemExit("Expected SVG source and output")
    try:
        result = finalize_svg(source.read_bytes(), embed_local=True)
        if len(sys.argv) == 4:
            policy_path = Path(sys.argv[3]).resolve()
            if workspace not in policy_path.parents or policy_path.stat().st_size > 100000:
                raise InvalidSVG("Copy policy must be a bounded workspace file")
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            extra = unexpected_copy(result, policy["exact_text"], policy["provided_text"])
            if extra:
                raise InvalidSVG("Remove unrequested text: " + "; ".join(extra))
    except InvalidSVG as exc:
        raise SystemExit(f"SVG rejected: {exc}") from exc
    output.write_bytes(result)
    print(f"SVG ready: {len(result)} bytes")
