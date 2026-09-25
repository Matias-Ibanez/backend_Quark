---
name: quark-style-product
description: "Trigger: producto, foto subida, remera, catálogo, venta. Compose product-led SVG posts around real user assets."
license: Apache-2.0
metadata:
  author: QUARK
  version: "1.0"
  hermes:
    tags: [marketing, product, svg, photo]
    requires_toolsets: [terminal, file]
---

## Activation Contract

Use when a supplied product image should be the hero. Pair with `quark-static-post`.

## Hard Rules

- Use the user's actual asset. The photo remains raster inside the vector SVG; typography, backgrounds and shapes stay vector.
- Do not stretch, recolor or replace the product. Use local rembg only if separation improves the composition.
- Do not invent price, discount, stock, material or product benefit.

## Decision Gates

| Asset | Treatment |
| --- | --- |
| Clean cutout | Large central or offset hero on a simple vector field |
| Lifestyle photo | Crop intentionally; protect the product and place text on a clear area |
| No photo supplied | Use a vector motif and message, or ask for the photo if indispensable |

## Execution Steps

1. Inspect the asset and choose a crop or cutout. Start from `assets/product.svg` only if its layout fits.
2. Make the product occupy at least a third of the canvas. Place headline and CTA in a separate readable zone.
3. Embed the uploaded photo with `svg_artifact.py` and inspect the Playwright preview at phone scale.

## Output Contract

Return an editable SVG source with embedded uploaded asset and matching PNG preview.

## References

- `assets/product.svg` — vector product layout example; replace its placeholder motif.
