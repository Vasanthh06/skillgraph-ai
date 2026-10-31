# Single-toggle correction

User-requested simplification: removed “Your space. Your perspective.” and Light/Dark/System buttons. One accessible switch named “Dark mode” uses aria-checked, an action tooltip, keyboard activation, and a sun/moon track. Selected theme persists using the existing provider. OS preference remains the initial default, not another visible control.

The graph's decorative “Build on your foundations” callout was absolutely positioned over the bottom text. It now occupies normal document flow below the card with 16px separation; it remains hidden on small mobile layouts. No API/backend changes.

Original files for this correction are backed up in `preservation/pre-toggle-files/`. Prior premium archive remains preserved as `/home/user/skillgraph_ui/pre-toggle-project.zip`; original Drive ZIP unchanged. Current screenshots supersede previous three-button images.

Executed: frontend build; 228 regression tests; 16 viewport/theme/persistence/no-overflow/no-callout-overlap checks at 320,375,390,430,768,1024,1280,1440; keyboard Space activation; login axe tagged scan with zero violations. See `docs/ui-evidence/toggle-results.json`, `toggle-build.txt`, `toggle-regression.txt`. Broader 473-check UI report describes the previous revision and was not rerun for this small correction. Physical devices still not tested.

Reproduce targeted browser test with UI_BASE_URL (default http://127.0.0.1:5174) and AXE_PATH to installed axe.min.js, then run `python scripts/toggle_browser_check.py`. Playwright/Chromium are separate QA tooling.
