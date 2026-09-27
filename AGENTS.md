# Project skills

Hermes loads its marketing skills from `hermes/skills/`, mounted by `compose.yaml`:

- `quark-marketing` — brief, asset use and video delivery.
- `quark-documents` — bounded PDF reading, scanned-page OCR and verified facts for content.
- `quark-narration` — Spanish spoken scripts, concrete hooks, verified claims and timing; the core guide also feeds MoneyPrinterTurbo.
- `manimce-best-practices` — vendored Manim Community guides, examples and templates from adithya-s-k/manim_skill, with a QUARK CPU/Docker profile; preserve LICENSE.txt and UPSTREAM.md when updating.
- `remotion-best-practices` — official Remotion composition, layout, animation, audio and caption references with a QUARK CPU/Docker profile; preserve UPSTREAM.md and the renderer's REMOTION-LICENSE.md. Motion graphics and original-photo videos use the preinstalled render-video.mjs runner, without project scaffolding.
- `quark-static-post` — safe native SVG export and Playwright preview.
- `quark-style-editorial`, `quark-style-product`, `quark-style-typographic` — reusable visual directions and vector examples.

When changing image delivery, preserve both the downloadable SVG and PNG preview used for Instagram publishing. Never commit keys or generated project data.
