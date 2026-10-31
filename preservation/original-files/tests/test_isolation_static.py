"""Static architecture checks. Pure Python: they read source files, so they run without any dependencies.

They fail the build if someone bypasses the user-scoped repository, accepts a user id from a client, hard-codes a
person into the product, or leaves personal data in browser storage.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backend" / "app"
USER_OWNED = ["UserSkillAssessment", "UserProgress", "UserProject", "Resume", "Certification", "InterviewAttempt", "UserActivity",
              "UserSkill", "SkillRecallSchedule", "Recommendation", "Roadmap", "Application", "Evidence", "SearchHistory", "UserEmbedding"]


def sources(*dirs):
    for d in dirs:
        for p in sorted((APP / d).glob("*.py")):
            yield p, p.read_text()


def test_handlers_never_query_user_owned_models_directly():
    owned = "|".join(USER_OWNED)
    # direct session access to a user-owned model; `UserScope(db, ...).add(Model(...))` is the sanctioned path
    pat = re.compile(r"select\(\s*(%s)\b|\bdb\.add\(\s*(%s)\(|db\.query\(\s*(%s)\b|db\.delete\(\s*(%s)\b" % (owned, owned, owned, owned))
    bad = [f"{p.name}: {m.group(0)}" for p, s in sources("api", "services") for m in pat.finditer(s)]
    assert not bad, "user-owned data must go through repositories.scoped.UserScope: " + "; ".join(bad)


def test_no_where_clause_hand_filters_user_id_in_handlers():
    bad = [p.name for p, s in sources("api", "services") if re.search(r"\.user_id\s*==", s)]
    assert not bad, f"hand-written user_id filters found (use UserScope): {bad}"


def test_no_endpoint_takes_a_user_id():
    bad = [p.name for p, s in sources("api") if re.search(r"def \w+\([^)]*\buser_id\b", s) or re.search(r"[\"'/]\{user_id\}", s)]
    assert not bad, f"endpoints must derive the user from the JWT, not accept an id: {bad}"


def test_every_user_owned_table_has_an_indexed_user_fk():
    text = "\n".join(p.read_text() for p in (APP / "models").glob("*.py"))
    blocks = re.split(r"\nclass ", text)
    owned = {}
    for b in blocks:
        m = re.match(r"(\w+)\(", b)
        if m and re.search(r"^\s+user_id: Mapped", b, re.M):
            owned[m.group(1)] = b
    assert set(USER_OWNED) - {"Evidence", "SearchHistory", "UserEmbedding"} <= set(owned) | {"UserActivity"}, set(owned)
    for name, body in owned.items():
        line = next(l for l in body.splitlines() if re.match(r"\s+user_id:", l))
        assert 'ForeignKey("users.id"' in line and 'ondelete="CASCADE"' in line, f"{name}.user_id must cascade from users.id"
        assert "String(36)" in line, f"{name}.user_id must be a UUID string"
        assert "index=True" in line or "unique=True" in line or name in ("UserSkill", "UserProgress"), f"{name}.user_id needs an index"


def test_user_ids_are_uuids_not_integers():
    user = (APP / "models" / "user.py").read_text()
    assert "uuid.uuid4()" in user and re.search(r"id: Mapped\[str\] = mapped_column\(String\(36\), primary_key=True", user)
    assert not re.search(r"user_id: Mapped\[int\]", "\n".join(p.read_text() for p in (APP / "models").glob("*.py")))


def test_no_public_upload_mount():
    main = (APP / "main.py").read_text()
    assert "StaticFiles" not in main and "app.mount(" not in main


def test_demo_mode_defaults_off_everywhere():
    assert re.search(r"DEMO_MODE: bool = False", (APP / "core" / "config.py").read_text())
    env = (ROOT / ".env.example").read_text()
    assert re.search(r"^DEMO_MODE=false$", env, re.M)


def test_no_personal_demo_data_in_product_code():
    offenders = []
    for base in (APP, ROOT / "frontend" / "src"):
        for p in base.rglob("*"):
            if p.suffix in (".py", ".ts", ".tsx") and re.search(r"Rahul|rahul@", p.read_text()):
                offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, f"a specific person appears in product code (demo users belong only in scripts/): {offenders}"


def test_frontend_has_no_hardcoded_personalised_values():
    bad = []
    for p in (ROOT / "frontend" / "src").rglob("*.ts*"):
        t = p.read_text()
        if re.search(r"readiness\s*=\s*\d|skillsRemaining\s*=|const nextSkill\s*=|const targetRole\s*=", t) or re.search(r"\b54%|12 skills", t):
            bad.append(p.name)
    assert not bad, bad


def test_browser_storage_holds_only_the_token():
    uses = {}
    for p in (ROOT / "frontend" / "src").rglob("*.ts*"):
        for m in re.finditer(r"(localStorage|sessionStorage|indexedDB)\.\w+\(([^)]*)\)", p.read_text()):
            uses.setdefault(p.name, []).append(m.group(0))
    flat = [u for v in uses.values() for u in v]
    assert flat and all("TOKEN_KEY" in u for u in flat), uses
    assert "sg_user" not in "\n".join(p.read_text() for p in (ROOT / "frontend" / "src").rglob("*.ts*"))


def test_demo_seed_script_is_demo_mode_only_and_flags_accounts():
    s = (ROOT / "scripts" / "seed_demo.py").read_text()
    assert "DEMO_MODE" in s and "is_demo_account" in s


# ---- explicit Save: forms are drafts, and only SaveBar-gated components may change the profile ----
FE = ROOT / "frontend" / "src"


def _fe(rel):
    return (FE / rel).read_text()


def test_every_form_component_has_a_save_bar():
    for rel in ("pages/Profile.tsx", "components/AssessmentForm.tsx", "components/RolePicker.tsx", "components/ResumePanel.tsx"):
        t = _fe(rel)
        assert re.search(r"import SaveBar from", t) and re.search(r"<SaveBar\b", t) and "onDiscard" in t, f"{rel} must render a SaveBar with Save and Discard"
        assert "useDirtyFlag" in t, f"{rel} must warn about unsaved changes"


def test_profile_changing_calls_only_live_in_save_gated_components():
    owners = {
        '"/assessment"': "components/AssessmentForm.tsx",
        '"/roles/target"': "components/RolePicker.tsx",
        '"/resume/confirm"': "components/ResumePanel.tsx",
        '"/resume/upload"': "components/ResumePanel.tsx",
    }
    for needle, owner in owners.items():
        # an actual write call to the endpoint (merely linking to a page called "/assessment" is fine)
        call = re.compile(r"http\.(?:post|put|upload)(?:<[^>]*>)?\(\s*" + re.escape(needle))
        callers = [str(p.relative_to(FE)) for p in FE.rglob("*.ts*") if call.search(p.read_text())]
        assert callers == [owner], f"{needle} is written from {callers}; it must only be written from {owner}, behind a Save button"


def test_drafts_store_only_edited_fields_not_snapshots():
    """A full-snapshot draft goes stale and can revert a change saved elsewhere (a real bug found in the preview)."""
    prof, asm = _fe("pages/Profile.tsx"), _fe("components/AssessmentForm.tsx")
    assert "Partial<Form>" in prof and "delete n[k]" in prof
    assert "delete n[s.slug]" in asm


def test_one_click_actions_confirm_with_a_saved_message():
    expected = {"pages/Roadmap.tsx": 1, "pages/Learn.tsx": 3, "pages/Jobs.tsx": 1}   # roadmap toggle; resource/project/certificate; save/apply
    for rel, n in expected.items():
        found = re.findall(r'useAction\([^\n]*"(?:Saved|Certification saved)[^"]*"\);', _fe(rel))
        assert len(found) >= n, f"{rel}: {len(found)} confirmed one-click actions, expected at least {n}"
    layout = _fe("layouts/AppLayout.tsx")
    assert "useNotice" in layout and 'role="status"' in layout and "Leave without saving" in layout


def test_resume_upload_is_staged_not_saved_in_backend():
    src = (APP / "api" / "modules_core.py").read_text()
    assert 'analysis_status="pending"' in src and "/resume/confirm" in src
    assert 'Resume.analysis_status == "completed"' in (APP / "services" / "analysis.py").read_text()


# ---- branding, theme and the data-driven dashboard ----
PUBLIC = FE.parent / "public"


def _is_png(p):
    return p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_logo_assets_exist_and_are_real_pngs():
    for name in ("logo-mark.png", "logo-full-dark.png", "logo-full-light.png", "favicon-64.png", "apple-touch-icon.png"):
        p = PUBLIC / name
        assert p.is_file() and p.stat().st_size > 1000 and _is_png(p), f"{name} missing or not a PNG"
    assert p.stat().st_size < 400_000, "logo assets should be web-sized"


def test_every_image_the_app_references_exists():
    refs = set()
    for f in FE.rglob("*.tsx"):
        refs |= set(re.findall(r'src="(/[\w.-]+\.png)"', f.read_text()))
    html = (FE.parent / "index.html").read_text()
    refs |= set(re.findall(r'href="(/[\w.-]+\.png)"', html))
    assert {"/logo-mark.png", "/logo-full-dark.png", "/favicon-64.png", "/apple-touch-icon.png"} <= refs, refs
    missing = [r for r in refs if not (PUBLIC / r.lstrip("/")).is_file()]
    assert not missing, f"referenced but missing from /public: {missing}"
    assert 'name="theme-color"' in html


def test_logo_is_used_in_the_shell_and_auth_screens():
    assert "/logo-mark.png" in _fe("layouts/AppLayout.tsx") and "gradient-text" in _fe("layouts/AppLayout.tsx")
    assert "/logo-full-dark.png" in _fe("layouts/AuthLayout.tsx") and "/logo-full-dark.png" in _fe("pages/Landing.tsx")


def test_the_dark_navy_theme_is_wired_through_tailwind():
    cfg = (FE.parent / "tailwind.config.js").read_text()
    assert '"#060B1E"' in cfg and "linear-gradient(135deg,#3B82FF" in cfg
    assert re.search(r"backgroundColor:\s*\{\s*white:", cfg), "bg-white must map to the dark panel surface or pages render as white blocks"
    css = _fe("index.css")
    assert "radial-gradient" in css and "color-scheme: dark" in css and "prefers-reduced-motion" in css


def test_navigation_matches_the_product_spec_with_a_career_profile_hub():
    layout = _fe("layouts/AppLayout.tsx")
    labels = re.findall(r'label: "([^"]+)"', layout)
    assert labels == ["Dashboard", "Resume Analysis", "Skill Graph", "Learning Roadmap", "Job Matching", "Project Recommendations", "Profile",
                      "Skill Gap", "Learn & Build", "Interview Prep", "Skill Explorer"], labels
    for page in ("Profile", "RolePage", "Assessment"):
        assert "<CareerTabs" in _fe(f"pages/{page}.tsx"), f"{page} must sit inside the Profile hub"
    assert "<CareerTabs" not in _fe("pages/Resume.tsx"), "Resume Analysis has its own navigation item"


def test_dashboard_visuals_come_from_backend_data_not_constants():
    d = _fe("pages/Dashboard.tsx")
    for field in ("d.next_best_action", "d.readiness_blockers", "d.skill_network", "d.journey", "d.skill_overview", "d.readiness_score"):
        assert field in d, f"dashboard must render {field} from the API"
    comp = _fe("components/dashboard.tsx")
    assert "strokeDashoffset={C * (1 - shown / 100)}" in comp and "useCountUp(v)" in comp, "the ring arc must be computed from its (eased) value"
    graph = _fe("components/SkillGraphView.tsx")
    assert re.search(r"network\.nodes", graph) and re.search(r"network\.edges", graph)
    assert not re.search(r"value=\{\s*\d+\s*\}", d + comp), "no hard-coded progress values"
    assert "Math.random" not in d + comp, "no fabricated data"


def test_visual_components_are_accessible():
    comp = _fe("components/dashboard.tsx")
    assert 'role="img" aria-label={`${label} ${v}%`}' in comp          # the ring is announced with its value
    graph = _fe("components/SkillGraphView.tsx")
    assert 'role="link"' in graph and "tabIndex={0}" in graph and "aria-label={`${n.name}" in graph   # nodes are keyboard- and screen-reader-reachable
    assert 'e.key === "Enter" || e.key === " "' in graph
    assert 'aria-label="Your career journey"' in comp
    assert "prefers-reduced-motion" in _fe("index.css")                # pulsing halo is disabled for reduced-motion users


# ---- redesign: navigation targets, filters, motion, honesty ----
def test_every_navigation_item_has_a_route():
    layout, app = _fe("layouts/AppLayout.tsx"), _fe("App.tsx")
    targets = re.findall(r'\{ to: "(/[\w-]+)", label:', layout)
    routes = set(re.findall(r'path="(/[\w-]+)"', app))
    assert len(targets) == 11 and not [t for t in targets if t not in routes], [t for t in targets if t not in routes]
    for page in ("SkillGraph", "Projects"):
        assert f'import {page} from "./pages/{page}"' in app


def test_internal_links_point_at_real_routes():
    routes = set(re.findall(r'path="(/[\w-]+)"', _fe("App.tsx"))) | {"/login", "/register", "/"}
    bad = set()
    for f in FE.rglob("*.tsx"):
        for m in re.finditer(r'(?:to=|nav\()["`{(]*"?`?(/[\w-]+)', f.read_text()):
            if m.group(1) not in routes:
                bad.add((f.name, m.group(1)))
    assert not bad, bad


def test_the_new_pages_have_real_filters_and_actions():
    jobs, proj, graph = _fe("pages/Jobs.tsx"), _fe("pages/Projects.tsx"), _fe("pages/SkillGraph.tsx")
    for ctl in ("jq", "jmin", "jexp", "jloc", "jst", "jsort"):
        assert f'id="{ctl}"' in jobs, ctl
    assert "Clear filters" in jobs and "application_status" in jobs and "clearStatus" in jobs and "aria-expanded" in jobs
    for ctl in ("Filter by difficulty", "pskill", "pstatus", "Ready to start"):
        assert ctl in proj, ctl
    assert "setStatus.mutate" in proj and "aria-pressed" in proj
    assert "Filter skills by state" in graph and "selected" in graph and "Take a quiz" in graph and "Clear filters" in graph


def test_sidebar_is_collapsible_and_pages_transition_on_route_change():
    layout = _fe("layouts/AppLayout.tsx")
    assert "aria-pressed={collapsed}" in layout and 'aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}' in layout
    assert '<div key={pathname} className="page-enter">' in layout, "the entrance must be keyed by route, not replay on every data change"


def test_motion_respects_reduced_motion_everywhere():
    css = _fe("index.css")
    block = css[css.rindex("@media (prefers-reduced-motion: reduce)"):]
    assert "animation: none !important" in block and "transition: none !important" in block
    hook = _fe("hooks/useMotion.ts")
    assert "prefers-reduced-motion: reduce" in hook and "if (reduced)" in hook, "counters must snap to the real value for reduced-motion users"
    assert "useReducedMotion" in _fe("components/ResumePanel.tsx") and "if (!reduced) setScanning(true)" in _fe("components/ResumePanel.tsx")


def test_real_results_are_never_artificially_delayed():
    """Timers are allowed only for presentation (toast expiry, draw-in, scan reveal, milestone celebration), never to hold back data."""
    allowed = {"store/notice.tsx", "components/SkillGraphView.tsx", "components/ResumePanel.tsx", "pages/Roadmap.tsx"}
    users = {str(f.relative_to(FE)).replace("\\", "/") for f in FE.rglob("*.ts*") if re.search(r"\bset(Timeout|Interval)\(", f.read_text())}
    assert users <= allowed, f"unexpected timers in: {sorted(users - allowed)}"
    scan = _fe("components/ResumePanel.tsx")
    assert "Skip animation" in scan and "1800" in scan, "the scan must be skippable and short"
    assert "Rule-based, from your evidence" in _fe("pages/Dashboard.tsx"), "AI insights must be labelled honestly"
    for f in FE.rglob("*.tsx"):
        assert not re.search(r"Math\.random|\blorem\b|GPT|LLM", f.read_text()), f"fabricated or overstated AI content in {f.name}"


def test_primary_actions_do_not_depend_on_native_form_submission():
    """Regression: sandboxed preview frames without `allow-forms` block form submission
    entirely, so a submit-button-only Log in never even fired its handler — the user stayed
    on /login ("clicking login does not navigate"). Verified in a real browser (Playwright,
    parent iframe with sandbox="allow-scripts"). Primary actions must run from a click
    handler, with form onSubmit kept only as a top-level fallback."""
    login, register = _fe("pages/Login.tsx"), _fe("pages/Register.tsx")
    assert 'type="button" onClick={doLogin}' in login and "onKeyDown={onEnter}" in login, "Log in must fire from a click (and Enter keydown), not only form submission"
    assert 'type="button" onClick={doRegister}' in register, "Create account must fire from a click, not only form submission"
    assert 'type="button" onClick={search}' in _fe("pages/Explore.tsx"), "Explore search must fire from a click"
    assert 'type="button" onClick={submitCert}' in _fe("pages/Learn.tsx"), "Add certificate must fire from a click"
    api = _fe("services/api.ts")
    assert "memoryToken" in api, "token storage must survive localStorage throwing in sandboxed frames"


def test_loading_empty_and_error_states_exist_on_every_data_page():
    for page in ("Dashboard", "SkillGraph", "Roadmap", "Jobs", "Projects"):
        t = _fe(f"pages/{page}.tsx")
        assert "PageSkeleton" in t and "ErrorNote" in t and "onRetry" in t, f"{page} needs loading and recoverable-error states"
    ui = _fe("components/ui.tsx")
    assert "Your data has not been lost" in ui and "EmptyState" in ui
    for page in ("Roadmap", "Jobs", "Projects"):
        assert "EmptyState" in _fe(f"pages/{page}.tsx"), f"{page} needs an empty state for filters with no results"
