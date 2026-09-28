---
name: manimce-best-practices
license: MIT
metadata:
  hermes:
    tags: [marketing, manim, animation, video]
    requires_toolsets: [terminal, file]
description: |
  Trigger when: (1) User mentions "manim" or "Manim Community" or "ManimCE", (2) Code contains `from manim import *`, (3) User runs `manim` CLI commands, (4) Working with Scene, MathTex, Create(), or ManimCE-specific classes.

  Best practices for Manim Community Edition - the community-maintained Python animation engine. Covers Scene structure, animations, LaTeX/MathTex, 3D with ThreeDScene, camera control, styling, and CLI usage.

  NOT for ManimGL/3b1b version (which uses `manimlib` imports and `manimgl` CLI).
---

## QUARK Docker profile

This section is a QUARK adaptation; upstream source and revision are recorded in [UPSTREAM.md](UPSTREAM.md). The following project constraints take precedence over generic examples below and in the rule files.

- Use the installed Manim Community Edition 0.20.1 with the Cairo renderer on CPU. Do not install ManimGL, switch to OpenGL, or reinstall dependencies. Render headlessly: omit `-p` and interactive/Jupyter commands. Prefer 2D for this service.
- Start with `rules/scenes.md`, `rules/positioning.md` and `rules/timing.md`; read only the additional guides needed by the scene (text, transformations, graphs or camera). Examples are building blocks, not finished ads to copy unchanged.
- Every Manim scene must use a pure black (#000000) background, including revisions. Set `config.background_color = BLACK` and `self.camera.background_color = BLACK` in every Scene. Do not override it with brand-colored backgrounds, gradients or full-screen filled rectangles. Inspect rendered frames to verify the background remains black. Brand colors apply only to foreground text, shapes and diagrams.
- Preserve the confirmed foreground brand colors, typography, dimensions and duration. Check installed fonts before choosing one; DejaVu Sans is available as a fallback. Do not force monochrome, monospace text, a math theme or a 3Blue1Brown palette onto a brand.
- Set both pixel dimensions and logical frame dimensions before constructing the scene. For a vertical 1080x1920 video, use an equivalent 9:16 frame (for example, frame_width=8 and frame_height=8*1920/1080). Scale the geometry for the frame; changing only pixel resolution can clip a horizontal layout.
- Draft at reduced resolution with the same aspect ratio, then render at the exact confirmed dimensions and 30 fps, unless a different frame rate was requested. Pass explicit `-r WIDTH,HEIGHT --fps 30 --renderer cairo`; do not let generic `-qh`/4K presets override the format. In `manim.cfg`, use supported keys under `[CLI]`, including `media_dir`, `renderer`, `preview=False` and dimensions; do not copy the illustrative `[output]`/`[renderer]` sections without checking the installed version.
- Keep readable margins, one focal visual per beat and meaningful transitions. Measure text and groups against the frame; fit long headlines before rendering. Show a change, relationship or demonstration rather than a series of identical title cards. Each beat must advance the message.
- Write `plan.md` and keep editable `script.py` in the assigned project directory. If there is voice, apply `quark-narration`, generate and measure the audio before timing the scenes; word count is only an estimate. Preserve exact user copy.
- Treat the requested duration as approximate: aim for that time, but allow up to 25% extra to finish the content and narration naturally (20 seconds may finish at 25). Do not cut speech, speed it up to meet an exact time, or pad the ending. If measured narration exceeds that margin, shorten secondary ideas before rendering; ask if exact user copy cannot fit.
- Render a complete narrative, stitch any separate scenes in order into a single `final.mp4`, and verify dimensions, duration and requested audio with `ffprobe`. Inspect beginning, middle and end frames, fix clipping and overlap, and allow the final message to finish. A rendered scene or a successful command alone is not a finished deliverable.

## How to use

Read individual rule files for detailed explanations and code examples:

### Core Concepts
- [rules/scenes.md](rules/scenes.md) - Scene structure, construct method, and scene types
- [rules/mobjects.md](rules/mobjects.md) - Mobject types, VMobject, Groups, and positioning
- [rules/animations.md](rules/animations.md) - Animation classes, playing animations, and timing

### Creation & Transformation
- [rules/creation-animations.md](rules/creation-animations.md) - Create, Write, FadeIn, DrawBorderThenFill
- [rules/transform-animations.md](rules/transform-animations.md) - Transform, ReplacementTransform, morphing
- [rules/animation-groups.md](rules/animation-groups.md) - AnimationGroup, LaggedStart, Succession

### Text & Math
- [rules/text.md](rules/text.md) - Text mobjects, fonts, and styling
- [rules/latex.md](rules/latex.md) - MathTex, Tex, LaTeX rendering, and coloring formulas
- [rules/text-animations.md](rules/text-animations.md) - Write, AddTextLetterByLetter, TypeWithCursor

### Styling & Appearance
- [rules/colors.md](rules/colors.md) - Color constants, gradients, and color manipulation
- [rules/styling.md](rules/styling.md) - Fill, stroke, opacity, and visual properties

### Positioning & Layout
- [rules/positioning.md](rules/positioning.md) - move_to, next_to, align_to, shift methods
- [rules/grouping.md](rules/grouping.md) - VGroup, Group, arrange, and layout patterns

### Coordinate Systems & Graphing
- [rules/axes.md](rules/axes.md) - Axes, NumberPlane, coordinate systems
- [rules/graphing.md](rules/graphing.md) - Plotting functions, parametric curves
- [rules/3d.md](rules/3d.md) - ThreeDScene, 3D axes, surfaces, camera orientation

### Animation Control
- [rules/timing.md](rules/timing.md) - Rate functions, easing, run_time, lag_ratio
- [rules/updaters.md](rules/updaters.md) - Updaters, ValueTracker, dynamic animations
- [rules/camera.md](rules/camera.md) - MovingCameraScene, zoom, pan, frame manipulation

### Configuration & CLI
- [rules/cli.md](rules/cli.md) - Command-line interface, rendering options, quality flags
- [rules/config.md](rules/config.md) - Configuration system, manim.cfg, settings

### Shapes & Geometry
- [rules/shapes.md](rules/shapes.md) - Circle, Square, Rectangle, Polygon, and geometric primitives
- [rules/lines.md](rules/lines.md) - Line, Arrow, Vector, DashedLine, and connectors

## Working Examples

Complete, tested example files demonstrating common patterns:

- [examples/basic_animations.py](examples/basic_animations.py) - Shape creation, text, lagged animations, path movement
- [examples/math_visualization.py](examples/math_visualization.py) - LaTeX equations, color-coded math, derivations
- [examples/updater_patterns.py](examples/updater_patterns.py) - ValueTracker, dynamic animations, physics simulations
- [examples/graph_plotting.py](examples/graph_plotting.py) - Axes, functions, areas, Riemann sums, polar plots
- [examples/3d_visualization.py](examples/3d_visualization.py) - ThreeDScene, surfaces, 3D camera, parametric curves

## Scene Templates

Copy and modify these templates to start new projects:

- [templates/basic_scene.py](templates/basic_scene.py) - Standard 2D scene template
- [templates/camera_scene.py](templates/camera_scene.py) - MovingCameraScene with zoom/pan
- [templates/threed_scene.py](templates/threed_scene.py) - 3D scene with surfaces and camera rotation

## Quick Reference

### Basic Scene Structure
```python
from manim import *

class MyScene(Scene):
    def construct(self):
        # Create mobjects
        circle = Circle()

        # Add to scene (static)
        self.add(circle)

        # Or animate
        self.play(Create(circle))

        # Wait
        self.wait(1)
```

### Render Command
```bash
# Basic render with preview
manim -pql scene.py MyScene

# Quality flags: -ql (low), -qm (medium), -qh (high), -qk (4k)
manim -pqh scene.py MyScene
```

### Key Differences from 3b1b/ManimGL

| Feature | Manim Community | 3b1b/ManimGL |
|---------|-----------------|--------------|
| Import | `from manim import *` | `from manimlib import *` |
| CLI | `manim` | `manimgl` |
| Math text | `MathTex(r"\pi")` | `Tex(R"\pi")` |
| Scene | `Scene` | `InteractiveScene` |
| Package | `manim` (PyPI) | `manimgl` (PyPI) |

### Jupyter Notebook Support

Use the `%%manim` cell magic:

```python
%%manim -qm MyScene
class MyScene(Scene):
    def construct(self):
        self.play(Create(Circle()))
```

### Common Pitfalls to Avoid

1. **Version confusion** - Ensure you're using `manim` (Community), not `manimgl` (3b1b version)
2. **Check imports** - `from manim import *` is ManimCE; `from manimlib import *` is ManimGL
3. **Outdated tutorials** - Video tutorials may be outdated; prefer official documentation
4. **manimpango issues** - If text rendering fails, check manimpango installation requirements
5. **PATH issues (Windows)** - If `manim` command not found, use `python -m manim` or check PATH

### Installation

```bash
# Install Manim Community
pip install manim

# Check installation
manim checkhealth
```

### Useful Commands

```bash
manim -pql scene.py Scene    # Preview low quality (development)
manim -pqh scene.py Scene    # Preview high quality
manim --format gif scene.py  # Output as GIF
manim checkhealth            # Verify installation
manim plugins -l             # List plugins
```
