---
name: quark-style-typographic
description: "Trigger: tipográfico, cita, dato, mensaje, promoción sin foto. Create message-led SVG graphics."
license: Apache-2.0
metadata:
  author: QUARK
  version: "1.0"
  hermes:
    tags: [marketing, typography, svg, design]
    requires_toolsets: [terminal, file]
---

## Activation Contract

Use when the message itself is the strongest visual. Pair with `quark-static-post`.

## Hard Rules

- Give one phrase or number dominance; avoid equal-weight text blocks.
- Use native SVG text and geometry; keep exact quotes and numbers supplied by the user.
- Do not fill empty space with arbitrary icons or fake photos.

## Decision Gates

| Content | Treatment |
| --- | --- |
| Quote or promise | Large phrase, deliberate line breaks, compact attribution |
| Statistic | Large number, precise label and restrained supporting context |

## Execution Steps

1. Start from `assets/typographic.svg` when useful; replace its sample data and color system.
2. Balance text blocks using asymmetry, clear spacing and a limited palette. Keep the CTA separate from the main message.
3. Render with Playwright and inspect at phone scale; shorten text or adjust line breaks before shrinking type.

## Output Contract

Return editable SVG and its matching PNG preview through the static-post workflow.

## References

- `assets/typographic.svg` — local vector type layout example.
