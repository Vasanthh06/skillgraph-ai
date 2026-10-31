# UI enhancement: inspection and implementation plan

Existing revision copied to a separate working tree. Original Drive ZIP, previous final ZIP and previous source remain untouched. No backend/API/model/algorithm changes are planned.

Inspection: React 18, React Router 6.30, Tailwind 3, existing CSS motion/reduced-motion hooks, SVG skill graph, data-driven Dashboard. Current tokens are dark-only hex values; hardcoded SVG labels/surfaces also need adaptation. No animation/WebGL dependency exists. Existing dirty-state provider warns on reload and sidebar links but not all browser-history actions. Existing public page is a small static intro and oversized logo.

Plan:
1. RGB CSS design tokens + centralized Light/Dark/System provider; synchronous bootstrap to avoid theme flash; visible shared toolbar.
2. Router-observed in-app history metadata for safe Back/Forward. Adopt React Router data-router wrapper to enable useBlocker for browser/buttons/links while dirty. No new authentication system or route contracts.
3. Product landing: prerequisite illustration, focusable/selectable SVG nodes, example roadmap, explanatory sections, real existing auth CTAs. Use 2D SVG + CSS depth instead of unnecessary Three.js.
4. Consistent interactions/semantic sections/reduced motion/IntersectionObserver reveals; preserve data-driven dashboard.
5. Build, full existing regression suite (update obsolete theme-specific static assertions with stronger new contracts), real Chromium theme/history/CTA/viewport checks, actual screenshots and remaining limitations.
