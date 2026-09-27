# Source and local adaptation

- Repository: https://github.com/adithya-s-k/manim_skill
- Source directory: `skills/manimce-best-practices`
- Pinned revision: `cef045011722d285692e3381d12d4d637da56e18`
- License: MIT, retained in `LICENSE.txt` with the author's copyright.
- Installed with the Codex skill-installer helper into `hermes/skills/`, not a global Codex directory. Only the Community Edition skill is included.
- QUARK modifications: `SKILL.md` adds license/Hermes metadata and a Docker profile covering CPU/Cairo, headless rendering, brand preferences, frame geometry, narration and final delivery. The upstream rules, examples and templates are preserved unchanged.

To update, review the new upstream revision, refresh this directory and reapply the local profile. Verify native Hermes skill loading and a Cairo render with the pinned Manim version before deployment. Do not download or upgrade skills during ordinary user requests.
