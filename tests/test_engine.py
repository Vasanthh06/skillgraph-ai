"""Pure-engine tests: no database, no network, no third-party packages."""
from app.engine import gap as G
from app.engine import interview as I
from app.engine import jobs as J
from app.engine import recommend as R
from app.engine import roadmap as RM
from app.engine.catalog import compact, get_catalog
from app.engine.knowledge import SELF_ONLY_CAP, SkillEvidence, UserState, build_profile, estimate, level_for
from app.graph import skill_graph as SG
from app.ml import semantic
from app.ml.embeddings import HashingEmbedder
from app.ml.vector_index import BruteForceIndex
from app.nlp import resume_parser as RP

cat = get_catalog()
ML = cat.roles["Machine Learning Engineer"]


def rahul_state(**kw):
    s = UserState(self_levels={"python": "intermediate", "sql": "intermediate", "pandas": "beginner", "numpy": "beginner",
                               "statistics": "beginner", "machine-learning": "beginner", "git": "intermediate"})
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def scores_of(state):
    return {k: v.score for k, v in build_profile(state).items()}


# ---- catalog integrity ----
def test_catalog_integrity():
    for s in cat.skills.values():
        assert all(p in cat.skills for p in s.prereqs)
        assert s.slug not in cat.all_prereqs(s.slug)  # no cycles
    for r in cat.roles.values():
        assert all(x.slug in cat.skills for x in r.skills)
    assert len(cat.roles) >= 8


# ---- normalisation (spec §10) ----
def test_react_variants_normalise_to_react():
    for v in ["ReactJS", "React.js", "React JS", "react"]:
        assert cat.resolve(v) == "react", v


def test_aliases():
    assert cat.resolve("sklearn") == "scikit-learn"
    assert cat.resolve("Node.js") == "nodejs"
    assert cat.resolve("CI/CD") == "ci-cd"
    assert cat.resolve("K8s") == "kubernetes"
    assert cat.resolve("not-a-skill-xyz") is None
    assert compact("React.js") == "reactjs"


def test_scan_ignores_false_positives_and_dedupes():
    text = "Strong attention to detail. Rest of the team. CV attached. Used React.js, python and Python."
    slugs = [h[0] for h in cat.scan(text)]
    assert slugs.count("react") == 1 and "python" in slugs
    assert "transformers" not in slugs and "rest-apis" not in slugs


# ---- knowledge model (spec §11, §40, §41) ----
def test_self_report_alone_is_capped_and_low_confidence():
    e = estimate("python", SkillEvidence(self=95))
    assert e.score == SELF_ONLY_CAP and e.capped and e.confidence <= 0.35


def test_hard_evidence_lifts_cap_and_confidence():
    e = estimate("python", SkillEvidence(self=80, resume=70, assessment=85, projects=80, interview=76, learning=75))
    assert e.score > 75 and e.level in ("advanced", "expert") and e.confidence > 0.8 and not e.capped


def test_weights_are_configurable():
    ev = SkillEvidence(self=20, assessment=100)
    heavy_assessment = estimate("x", ev, {"resume": .1, "self": .1, "assessment": .6, "projects": .1, "learning": .05, "interview": .05})
    default = estimate("x", ev)
    assert heavy_assessment.score > default.score


def test_disagreement_lowers_confidence():
    agree = estimate("x", SkillEvidence(self=70, assessment=72))
    clash = estimate("x", SkillEvidence(self=95, assessment=10))
    assert clash.confidence < agree.confidence


def test_levels():
    assert [level_for(x) for x in (0, 10, 50, 70, 90)] == ["none", "beginner", "intermediate", "advanced", "expert"]


def test_resume_plus_assessment_combined():
    s = rahul_state(resume={"python": 70.0}, assessment={"python": 80.0})
    p = build_profile(s)["python"]
    assert 60 < p.score < 80 and not p.capped


# ---- gap engine (spec §14-16) ----
def test_demo_user_gap_shape():
    sc = scores_of(rahul_state())
    g = G.analyze(cat, ML, sc)
    status = {i.slug: i.status for i in g.items}
    assert status["python"] == "strong" and status["pandas"] == "weak" and status["pytorch"] == "missing"
    assert 0 < g.skills_readiness < 40


def test_learn_order_respects_prerequisites():
    g = G.analyze(cat, ML, scores_of(rahul_state()))
    pos = {s: i for i, s in enumerate(g.order)}
    for s in g.order:
        for p in cat.skills[s].prereqs:
            if p in pos:
                assert pos[p] < pos[s], f"{p} must precede {s}"


def test_prioritised_not_alphabetical():
    g = G.analyze(cat, ML, scores_of(rahul_state()))
    assert g.order != sorted(g.order)
    assert g.order.index("machine-learning") < g.order.index("deep-learning") < g.order.index("pytorch")


def test_supporting_prerequisite_added():
    g = G.analyze(cat, ML, scores_of(rahul_state()))
    linux = next(i for i in g.items if i.slug == "linux")
    assert linux.supporting and linux.group == "Prerequisites"


def test_critical_skills_unlock_many():
    g = G.analyze(cat, ML, scores_of(rahul_state()))
    crit = {i.slug for i in g.critical}
    assert "machine-learning" in crit and "aws" not in crit


def test_readiness_breakdown_and_overall():
    g = G.analyze(cat, ML, scores_of(rahul_state()))
    assert "Machine Learning" in g.group_readiness and g.group_readiness["Deployment"] == 0
    o = G.overall_readiness(g.skills_readiness, 0, None)
    assert o["interview"] is None and o["projects"] == 0 and o["overall"] <= round(g.skills_readiness)


# ---- roadmap (spec §22-23, §57) ----
def test_roadmap_statuses_and_unlock():
    s = rahul_state()
    sc = scores_of(s)
    nodes = RM.build(cat, G.analyze(cat, ML, sc), sc, set())
    st = {n.slug: n.status for n in nodes}
    assert st["python"] == "completed" and st["machine-learning"] == "locked" and st["scikit-learn"] == "locked"
    assert sum(1 for n in nodes if n.status == "current") == 1
    blocked = next(n for n in nodes if n.slug == "machine-learning").blocked_by
    assert "pandas" in blocked or "statistics" in blocked

    s.completed_roadmap |= {"statistics", "pandas", "numpy"}
    sc = scores_of(s)
    nodes = RM.build(cat, G.analyze(cat, ML, sc, s.completed_roadmap), sc, s.completed_roadmap)
    st = {n.slug: n.status for n in nodes}
    assert st["machine-learning"] == "current" and st["scikit-learn"] == "locked"

    s.completed_roadmap.add("machine-learning")
    sc = scores_of(s)
    nodes = RM.build(cat, G.analyze(cat, ML, sc, s.completed_roadmap), sc, s.completed_roadmap)
    assert {n.slug: n.status for n in nodes}["scikit-learn"] in ("current", "available")


def test_progress_changes_scores_per_spec_example():
    before = scores_of(rahul_state())["statistics"]
    after = scores_of(rahul_state(completed_roadmap={"statistics"}, assessment={"statistics": 90.0}))["statistics"]
    assert after > before + 25


def test_target_role_change_keeps_skills():
    sc = scores_of(rahul_state())
    ds = G.analyze(cat, cat.roles["Data Scientist"], sc)
    ml = G.analyze(cat, ML, sc)
    assert {i.slug for i in ds.items} != {i.slug for i in ml.items}
    assert next(i for i in ds.items if i.slug == "python").score == next(i for i in ml.items if i.slug == "python").score


# ---- jobs (spec §26-28) ----
def test_job_match_explained():
    sc = scores_of(rahul_state())
    m = J.match_job(cat, cat.jobs["ml-intern-1"], sc, ML, "fresher", "Bengaluru")
    assert 0 < m["match"] <= 100 and "Python" in m["have"] and m["missing"] and "primary remaining gap" in m["explanation"]
    assert m["is_demo"] is True


def test_jobs_ranked_by_fit():
    sc = scores_of(rahul_state())
    ranked = J.rank_jobs(cat, sc, ML, "fresher", "Bengaluru")
    assert ranked[0]["match"] >= ranked[-1]["match"] and ranked[0]["title"] != "UI/UX Designer"


def test_experience_penalty():
    sc = scores_of(rahul_state())
    fresher = J.match_job(cat, cat.jobs["ml-eng-1"], sc, ML, "fresher", "Remote")
    senior = J.match_job(cat, cat.jobs["ml-eng-1"], sc, ML, "3-5", "Remote")
    assert senior["components"]["experience"] > fresher["components"]["experience"]


JD = """Machine Learning Engineer

Responsibilities:
- Build and deploy models
- Maintain data pipelines

Requirements:
- 2+ years of experience with Python and SQL
- Strong knowledge of PyTorch and Docker
- B.Tech or Master's degree

Nice to have:
- Experience with AWS and Kubernetes
"""


def test_jd_analysis():
    sc = scores_of(rahul_state())
    r = J.analyze_jd(cat, JD, sc)
    assert {"Python", "SQL", "PyTorch", "Docker"} <= set(r["required_skills"])
    assert {"AWS", "Kubernetes"} <= set(r["preferred_skills"])
    assert r["experience_years"] == 2 and r["education"]
    assert "Python" in r["strong"] and "PyTorch" in r["missing"] and r["responsibilities"]


# ---- interview (spec §29-31) ----
def test_score_mcq_exact():
    q = next(q for q in cat.questions.values() if q.category == "mcq")
    assert I.score_answer(q, None, q.answer_index, None) == (100.0, "exact")
    assert I.score_answer(q, None, (q.answer_index + 1) % len(q.options), None)[0] == 0.0


def test_open_answer_is_keyword_based_and_short_answers_capped():
    q = next(q for q in cat.questions.values() if q.category == "technical" and q.skill == "machine-learning")
    long = "Bias is error from wrong assumptions, variance is sensitivity to training data. A complex model overfits (high variance) and a simple one underfits (high bias); regularization trades one for the other."
    s_long, m = I.score_answer(q, long, None, None)
    s_short, _ = I.score_answer(q, "bias variance overfit underfit", None, None)
    assert m == "keyword_coverage" and s_long > 70 and s_short <= 40


def test_self_rated_categories():
    q = next(q for q in cat.questions.values() if q.category == "behavioral")
    assert I.score_answer(q, "x", None, 4) == (80.0, "self_rated")


def test_adaptive_selection_prefers_weak_role_skills():
    sc = scores_of(rahul_state())
    imp = {r.slug: r.importance for r in ML.skills}
    qs = I.select_questions(cat, sc, imp, n=6, category="mcq")
    skills = [q.skill for q in qs]
    assert "python" not in skills[:2]  # strong skill is not first
    assert any(s in ("machine-learning", "model-evaluation", "deep-learning", "pytorch", "scikit-learn") for s in skills[:4])


def test_focus_skills_for_job():
    sc = scores_of(rahul_state())
    qs = I.select_questions(cat, sc, {}, focus_skills=["docker"], n=3)
    assert all(q.skill == "docker" for q in qs)


def test_readiness_excludes_unpractised_components():
    assert I.readiness([], None, None)["overall"] is None
    r = I.readiness([{"category": "mcq", "score": 100}, {"category": "mcq", "score": 50}, {"category": "hr", "score": 80}], 60, 30)
    assert r["components"]["technical"] == 75 and r["components"]["communication"] == 80 and r["components"]["coding"] is None
    assert 0 < r["overall"] <= 100


# ---- recommendations (spec §44) ----
def test_next_skill_is_explainable():
    sc = scores_of(rahul_state())
    g = G.analyze(cat, ML, sc)
    rec = R.next_skill(cat, g, sc, ML.name)
    assert rec and all(rec[k] for k in ("what", "why", "why_now", "impact", "next")) and rec["source"] == "rules"
    assert rec["slug"] not in ("deep-learning", "aws")


def test_impact_uses_demo_dataset():
    sc = scores_of(rahul_state())
    g = G.analyze(cat, ML, sc)
    rec = R.explain_skill(cat, "python", g, sc, ML.name) if any(i.slug == "python" for i in g.items) else R.explain_skill(cat, "machine-learning", g, sc, ML.name)
    assert "demo dataset" in rec["impact"] or "Importance" in rec["impact"]


def test_struggling_recommends_prereqs():
    sc = scores_of(rahul_state())
    g = G.analyze(cat, ML, sc)
    out = R.struggling(cat, sc, {"machine-learning": (30.0, 3), "python": (30.0, 1)}, g)
    assert len(out) == 1 and out[0]["skill"] == "Machine Learning" and out[0]["review_first"]


def test_sequential_intent():
    sc = scores_of(rahul_state())
    it = R.infer_intent(cat, ["python", "pandas", "numpy", "machine-learning", "scikit-learn"], sc)
    assert it and "Machine Learning" in it["label"] or "Data" in it["label"]
    assert it["source"] == "heuristic" and R.infer_intent(cat, ["python"], sc) is None


# ---- resume (spec §10, §32-33) ----
RESUME = """Rahul Kumar
rahul@example.com | +91 98765 43210

SKILLS
Python, SQL, Pandas, ReactJS

EXPERIENCE
- Built a churn model with Python and scikit-learn, reaching 0.82 AUC on 7,000 rows
- Responsible for reporting in a small team
"""


def test_resume_parse_and_normalise():
    p = RP.parse(cat, RESUME)
    assert p.skills["react"]["evidence"] == "listed" and p.skills["python"]["evidence"] == "applied"
    assert p.has_email and p.has_phone
    ev = RP.resume_evidence(p)
    assert ev["python"] > ev["sql"]


def test_resume_analysis_flags_without_inventing():
    p = RP.parse(cat, RESUME)
    a = RP.analyze(cat, p, ML, {"statistics": 50})
    assert any("Weak phrasing" in t for t in a["tips"])
    assert any(g["skill"] == "Statistics" for g in a["evidence_gaps"])
    assert 0 <= a["role_match"] <= 100 and 0 <= a["ats_score"] <= 100


def test_unsupported_and_empty_resume():
    for data, name in [(b"abc", "x.exe"), (b"tiny", "x.txt"), (b"not a zip", "x.docx")]:
        try:
            RP.extract_text(data, name)
            assert False, name
        except RP.UnsupportedResume:
            pass


def test_docx_extraction_roundtrip():
    import io
    import zipfile

    xml = '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' \
          '<w:p><w:r><w:t>SKILLS</w:t></w:r></w:p><w:p><w:r><w:t>Python, SQL and Docker used in several production projects at work.</w:t></w:r></w:p></w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    text = RP.extract_text(buf.getvalue(), "cv.docx")
    assert "Python" in text and "SKILLS" in text


# ---- search, graph, vectors (spec §34-37, §42, §59) ----
def test_search_exact_alias_and_typo():
    assert semantic.search(cat, "ReactJS")["exact"] == "react"
    assert "machine-learning" in [r["slug"] for r in semantic.search(cat, "machin learning")["related"]]
    assert semantic.search(cat, "")["matches"] == []
    r = semantic.search(cat, "zzzzqqqq")
    assert r["exact"] is None and r["related"] == []


def test_unknown_skill_is_not_fabricated():
    assert cat.resolve("quantum basket weaving") is None


def test_react_learning_path_matches_spec_order():
    path = SG.learning_path(cat, "react")
    assert path[-1] == "react" and set(path[:-1]) == {"javascript", "html", "css"}


def test_graph_edges_point_prereq_to_dependent():
    g = SG.neighborhood(cat, "pytorch")
    assert {"source": "deep-learning", "target": "pytorch"} in g["edges"]


def test_skill_detail_links_projects_jobs_questions():
    d = SG.skill_detail(cat, "docker")
    assert d["projects"] and d["jobs"] and d["questions"] > 0 and d["career_paths"] and d["docs_url"]
    assert SG.skill_detail(cat, "python")["taxonomy"]["children"]


def test_embedder_and_index():
    e = HashingEmbedder()
    a, b, c = e.embed(["react", "reactjs", "kubernetes"])
    dot = lambda x, y: sum(p * q for p, q in zip(x, y))
    assert dot(a, b) > dot(a, c)
    idx = BruteForceIndex(e.dim)
    idx.add(["react", "k8s"], [a, c])
    assert idx.search(b, 1)[0][0] == "react"


def test_nearest_role_for_custom_role():
    name, score = semantic.nearest_role(cat, "Applied Machine Learning Researcher")
    assert name in cat.roles and score > 0


# ---- Next Best Action, readiness blockers, skill network (spec §15, §23) ----
from app.engine import actions as ACT


def _ctx(state=None, role="Machine Learning Engineer", **over):
    state = state or rahul_state()
    est = build_profile(state)
    sc = {k: v.score for k, v in est.items()}
    r = cat.roles[role]
    g = G.analyze(cat, r, sc, state.completed_roadmap)
    rec = R.next_skill(cat, g, sc, r.name)
    kw = dict(needs=None, role=r, gap=g, scores=sc, estimates=est, declared_done=set(state.completed_roadmap) | set(state.completed_resources),
              attempt_avgs={}, projects_done=0, project={"title": "House Price Regression", "why": "Builds ML."}, attempts=0, resume_present=False, recommended=rec)
    kw.update(over)
    return kw, sc, r


def test_skills_readiness_matches_the_gap_engine():
    sc = scores_of(rahul_state())
    assert abs(G.skills_readiness(ML, sc) - G.analyze(cat, ML, sc).skills_readiness) < 0.06
    assert G.overall_readiness(40, 1, None)["overall"] == round(G.overall_float(40, 1, None))


def test_blockers_are_ranked_by_simulated_gain_and_the_gain_is_real():
    sc = scores_of(rahul_state())
    b = ACT.readiness_blockers(cat, ML, sc, 0, None)
    assert b["goal"] == 80 and not b["reached"] and b["to_go"] == 80 - b["current"]
    gains = [x["gain"] for x in b["blockers"] if x["gain"] is not None]
    assert gains == sorted(gains, reverse=True) and all(g > 0 for g in gains)
    top = next(x for x in b["blockers"] if x["kind"] == "skill")
    sim = {**sc, top["slug"]: float(G.TARGET)}
    real = G.overall_float(G.skills_readiness(ML, sim), 0, None) - G.overall_float(G.skills_readiness(ML, sc), 0, None)
    assert abs(real - top["gain"]) < 0.06, "the reported gain must equal a recomputation"
    assert any(x["kind"] == "project" for x in b["blockers"])
    assert b["blockers"][-1]["kind"] == "interview" and b["blockers"][-1]["gain"] is None   # unmeasured, honestly marked


def test_blockers_react_to_evidence():
    sc = scores_of(rahul_state())
    done3 = ACT.readiness_blockers(cat, ML, sc, 3, 85.0)
    assert not any(x["kind"] == "project" for x in done3["blockers"]) and not any(x["kind"] == "interview" for x in done3["blockers"])
    strong = {**sc, **{r.slug: 90.0 for r in ML.skills}}
    assert ACT.readiness_blockers(cat, ML, strong, 3, 90.0)["reached"] is True
    assert ACT.readiness_blockers(cat, ML, strong, 3, 90.0)["blockers"] == []
    assert any(x["kind"] == "interview" and x["gain"] for x in ACT.readiness_blockers(cat, ML, sc, 0, 40.0)["blockers"])


def test_nba_onboarding_comes_first():
    kw, _, _ = _ctx()
    assert ACT.next_best_action(cat, **{**kw, "needs": "target_role", "role": None, "gap": None})["type"] == "role"
    a = ACT.next_best_action(cat, **{**kw, "needs": "assessment", "gap": None})
    assert a["type"] == "assessment" and a["route"] == "/assessment" and "Machine Learning Engineer" in a["reason"]


def test_nba_learns_the_next_skill_with_a_reason():
    kw, _, _ = _ctx()
    a = ACT.next_best_action(cat, **kw)
    assert a["type"] == "learn" and a["skill"] == "statistics" and a["title"] == "Learn Statistics" and len(a["reason"]) > 40
    assert a["route"] == "/learn?skill=statistics" and a["source"] == "rules"


def test_nba_verifies_a_declared_but_unproven_skill():
    st = rahul_state(completed_roadmap={"statistics"})
    kw, _, _ = _ctx(st)
    a = ACT.next_best_action(cat, **kw)
    assert a["type"] == "verify" and a["skill"] == "statistics" and "nothing proves it" in a["reason"]
    st2 = rahul_state(completed_roadmap={"statistics"}, assessment={"statistics": 85.0})   # a quiz now backs it
    kw2, _, _ = _ctx(st2)
    assert ACT.next_best_action(cat, **kw2)["type"] != "verify"


def test_nba_prefers_reviewing_foundations_when_struggling():
    kw, _, _ = _ctx()
    a = ACT.next_best_action(cat, **{**kw, "attempt_avgs": {"machine-learning": (22.0, 3)}})
    assert a["type"] == "review" and "22%" in a["reason"] and a["skill"] in ("statistics", "numpy", "pandas", "machine-learning")
    assert ACT.next_best_action(cat, **{**kw, "attempt_avgs": {"machine-learning": (22.0, 1)}})["type"] != "review"   # one attempt isn't a pattern


def test_nba_suggests_a_first_project_then_interviews():
    # a user with solid, quiz-verified foundations but no project and no interview practice yet
    base = ["python", "sql", "git", "statistics", "probability", "linear-algebra", "numpy", "pandas", "machine-learning", "feature-engineering", "model-evaluation", "scikit-learn"]
    st = UserState(self_levels={s: "intermediate" for s in base}, assessment={s: 80.0 for s in base})
    kw, sc, r = _ctx(st)
    assert G.skills_readiness(r, sc) >= 40
    a = ACT.next_best_action(cat, **kw)
    assert a["type"] == "project" and "House Price Regression" in a["title"]
    b = ACT.next_best_action(cat, **{**kw, "projects_done": 1})
    assert b["type"] == "interview" and b["route"] == "/interview"
    c = ACT.next_best_action(cat, **{**kw, "projects_done": 1, "attempts": 3})
    assert c["type"] == "learn"


def test_nba_when_everything_is_covered_puts_evidence_to_work():
    strong = UserState(self_levels={r.slug: "advanced" for r in ML.skills}, assessment={r.slug: 90.0 for r in ML.skills})
    kw, _, _ = _ctx(strong)
    kw.update(recommended=None, gap=G.analyze(cat, ML, kw["scores"]), projects_done=3, attempts=5)   # skills, projects and practice are all in place
    assert ACT.next_best_action(cat, **kw)["type"] == "resume"
    assert ACT.next_best_action(cat, **{**kw, "resume_present": True})["type"] == "jobs"
    assert ACT.next_best_action(cat, **{**kw, "projects_done": 0})["type"] == "project"        # no project yet: build one before applying


def test_explaining_a_supporting_prerequisite_never_crashes():
    """Regression: a prerequisite with no unmet dependents used to raise IndexError in the explanation text."""
    st = rahul_state(completed_roadmap={"machine-learning", "scikit-learn", "deep-learning", "neural-networks", "pytorch", "docker", "aws", "fastapi", "model-evaluation", "feature-engineering", "transformers", "cnn", "rnn", "tensorflow"})
    sc = scores_of(st)
    g = G.analyze(cat, ML, sc, st.completed_roadmap)
    for item in g.items:
        if item.status != "strong":
            R.explain_skill(cat, item.slug, g, sc, ML.name)   # must not raise
    R.next_skill(cat, g, sc, ML.name)


def test_skill_network_shape():
    sc = scores_of(rahul_state())
    g = G.analyze(cat, ML, sc)
    n = ACT.skill_network(cat, g, current="statistics")
    ids = {x["id"] for x in n["nodes"]}
    assert ids == {i.slug for i in g.items} and sum(1 for x in n["nodes"] if x["current"]) == 1
    assert all(e["source"] in ids and e["target"] in ids for e in n["edges"])
    assert {"source": "numpy", "target": "pandas"} in n["edges"] and {"source": "pandas", "target": "numpy"} not in n["edges"]
    assert all(cat.depth(e["source"]) < cat.depth(e["target"]) for e in n["edges"])      # acyclic, left-to-right
    st = {x["id"]: x["status"] for x in n["nodes"]}
    assert st["python"] == "strong" and st["pytorch"] == "missing"


def test_rounding_is_half_up_not_bankers():
    assert [G.half_up(x) for x in (98.5, 99.5, 0.5, 97.4, 97.6)] == [99, 100, 1, 97, 98]
    # 40 skills / 100 projects / no interview -> an exact .5 in the blend must round up
    assert G.overall_readiness(98.5, 3, None)["skills"] == 99


def test_skill_state_acquired_in_progress_missing():
    assert ACT.skill_state("strong", False) == "acquired" and ACT.skill_state("strong", True) == "acquired"
    assert ACT.skill_state("weak", False) == "in_progress"
    assert ACT.skill_state("missing", True) == "in_progress"      # the step the user is on now counts as in progress
    assert ACT.skill_state("missing", False) == "missing"


def test_network_nodes_carry_a_consistent_state():
    sc = scores_of(rahul_state())
    g = G.analyze(cat, ML, sc)
    n = ACT.skill_network(cat, g, current="statistics")
    st = {x["id"]: x["state"] for x in n["nodes"]}
    assert st["python"] == "acquired" and st["statistics"] == "in_progress" and st["pytorch"] == "missing"
    assert all(x["state"] == "acquired" for x in n["nodes"] if x["status"] == "strong")
    assert {x["state"] for x in n["nodes"]} <= {"acquired", "in_progress", "missing"}
