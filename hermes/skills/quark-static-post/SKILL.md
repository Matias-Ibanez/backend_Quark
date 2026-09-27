---
name: quark-static-post
description: "Trigger: post, publicación, banner, flyer, imagen estática. Create editable SVG ads and a Playwright PNG preview."
license: Apache-2.0
metadata:
  author: QUARK
  version: "1.1"
  hermes:
    tags: [marketing, social-media, static, svg, playwright]
    requires_toolsets: [terminal, file]
---

## Activation Contract

Use for any static marketing image. Use `quark-marketing` for the brief (do not reload a guide already included in the task) and choose just one style skill: `quark-style-editorial`, `quark-style-product`, or `quark-style-typographic`. Keep the source for later revisions.

## Hard Rules

- Draw text, shapes, icons and diagrams as native SVG elements. Never trace a screenshot or save a PNG with an `.svg` extension.
- Use uploaded photos only when relevant; photos embedded in SVG remain raster. Do not invent prices, claims, contacts or photographs.
- If copy_mode is exact, use only the confirmed wording plus the supplied brand/industry label. Line breaks may change; never add a supporting sentence, slogan, benefit or new CTA. Keep caption text separate from the SVG. Check this in visual QA.
- Keep all visible copy inside generous safe margins (at least 3% on every edge, checked automatically for native SVG text). Use a short headline and one CTA. Do not ship sample copy or untouched templates.
- Do not use `<script>`, `<style>`, `foreignObject`, remote links, external fonts or executable attributes. Use SVG presentation attributes and local uploaded images.

## Decision Gates

| Brief | Style |
| --- | --- |
| Product or uploaded photo | `quark-style-product` |
| Announcement, story, campaign concept | `quark-style-editorial` |
| Quote, data or message-led post | `quark-style-typographic` |

## Execution Steps

1. Write `plan.md` and an editable `source.svg` at `/workspace/hermes/PROJECT/`. Use 1080×1350 for feed or 1080×1920 for story unless requested otherwise. Start from a style skill's local SVG asset when useful, then customize it substantially.
2. If using an uploaded photo, reference it in `<image href="file:///workspace/assets/NAME.png">` while editing. Preserve its aspect ratio. Run `/opt/hermes/.venv/bin/python /opt/quark-renderer/svg_artifact.py /workspace/hermes/PROJECT/source.svg /workspace/hermes/PROJECT/final.svg` to embed the photo and reject unsafe SVG. If the task provides copy-policy.json, pass its path as the third argument after SOURCE and FINAL; remove rejected extra phrases from the source, never edit the policy to permit them. This local check must pass before rendering.
3. Run `node /opt/quark-renderer/render.mjs /workspace/hermes/PROJECT/final.svg /workspace/hermes/PROJECT/final.png 1080 1350` (change dimensions for the brief). Inspect this final PNG visually. Revise `source.svg`, finalize and rerender only when QA finds an issue. When the SVG has not changed, keep the approved PNG as the deliverable; do not render the same SVG a second time just to rename a draft. The validator catches technical errors; you must catch weak layout, type hierarchy and contrast.
4. Write `caption.txt` with the plan/source in a single file operation when possible. Confirm both final files are nonempty and that the PNG corresponds to the final SVG.
5. For a carousel, finalize all SVG sources first, then write a local JSON manifest (1–10 jobs) and call `node /opt/quark-renderer/render.mjs --batch /workspace/hermes/PROJECT/render-jobs.json`. Each job is `{"source":"/workspace/hermes/PROJECT/final-01.svg","output":"/workspace/hermes/PROJECT/final-01.png","width":1080,"height":1350}`. A single Chromium renders sequentially with an isolated page per slide, suitable for CPU-only machines. Inspect every PNG; correct and rerender only affected slides. Do not parallelize multiple Chromium processes on the i3.

## Output Contract

Deliver one `final.svg` with a matching `final.png` preview, editable `source.svg` and `caption.txt`. Describe the result to the user without paths or implementation details.

## References

- Style skills and their local SVG assets: `quark-style-editorial`, `quark-style-product`, `quark-style-typographic`.
