"""Static safety/architecture contracts in addition to real browser acceptance."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
F=R/'frontend/src'

def test_shared_theme_and_prepaint_bootstrap():
    html=(R/'frontend/index.html').read_text()
    assert html.index("sg_theme") < html.index('type="module"')
    assert 'dataset.theme' in html
    main=(F/'main.tsx').read_text()
    assert '<ThemeProvider>' in main and '<ScrollRestoration' in main
    app=(F/'App.tsx').read_text()
    assert '<ThemeBar />' in app
    provider=(F/'store/theme.tsx').read_text()
    assert 'addEventListener("change"' in provider and 'addEventListener("storage"' in provider


def test_graph_semantic_theme_colors():
    for file in ['components/SkillGraphView.tsx','components/SkillGraph.tsx']:
        source=(F/file).read_text()
        assert 'var(--' in source
        assert '"#B6C0E4"' not in source and '"#0E1636"' not in source


def test_history_uses_deltas_not_external_urls():
    source=(F/'store/navigation.tsx').read_text()
    assert 'navigate(-1)' in source and 'navigate(1)' in source
    assert 'history.length' not in source.replace('history.length,','')
    assert 'pushState(' not in source and 'replaceState(' not in source
    assert 'navigate("/dashboard", {replace:true})' in source
    layout=(F/'layouts/AppLayout.tsx').read_text()
    assert 'useBlocker(' in layout and 'aria-modal="true"' in layout and 'e.key === "Tab"' in layout


def test_no_webgl_or_extra_animation_library_needed():
    source=(F/'components/IllustrativeGraph.tsx').read_text()
    assert '<svg' in source and 'Illustrative graph' in source and 'tabIndex={0}' in source
    manifest=(R/'frontend/package.json').read_text()
    for name in ['three','framer-motion','gsap']:
        assert '"'+name+'"' not in manifest


def test_ui_work_preserves_cookie_auth_photo_loading():
    source=(F/'components/Avatar.tsx').read_text()
    assert 'credentials: "same-origin"' in source
    assert 'Authorization:' not in source  # do not send an in-memory sentinel as a bearer token
    api=(F/'services/api.ts').read_text()
    assert 'localStorage' not in api and 'sessionStorage' not in api
