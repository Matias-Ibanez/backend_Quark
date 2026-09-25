---
name: quark-style-editorial
description: "Trigger: editorial, anuncio, lanzamiento, campaña conceptual. Build distinctive editorial SVG posts."
license: Apache-2.0
metadata:
  author: QUARK
  version: "1.0"
  hermes:
    tags: [marketing, editorial, svg, design]
    requires_toolsets: [terminal, file]
---

## Activation Contract

Use for announcements, launches and concept-led campaigns. Pair with `quark-static-post`.

## Hard Rules

- Establish one typographic focal point and a clear reading path. Avoid a centered title with scattered decoration.
- Keep contrast high and make the headline legible when scaled to a phone.
- Use native SVG shapes, paths and text. Never fabricate a brand promise or event detail.

## Decision Gates

| Message | Composition |
| --- | --- |
| Short and bold | Oversized headline, small eyebrow, narrow supporting copy |
| Longer explanation | Strong headline plus one compact text block and a quiet CTA |

## Execution Steps

1. Copy `assets/editorial.svg` to the project as a starting point if it fits the brief.
2. Replace every sample word, palette and decorative device with choices tied to the user's brand. Limit type to two weights and three scale levels.
3. Leave at least 64 px around essential text; inspect the rendered draft for unwanted line breaks and overlap.

## Output Contract

Return an editable SVG source through the static-post workflow, with its matching PNG preview.

## References

- `assets/editorial.svg` — local vector composition example.
