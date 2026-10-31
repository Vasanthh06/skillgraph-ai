"""Integrated intelligence: bottleneck detection, confidence calibration and spaced recall.

Covers the pure formulas, the API loop (assessment -> check -> learning -> recall), per-user isolation
and the data-preserving schema migration.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, inspect, text

from app.core.migrations import migrate_intelligence
from app.engine import gap as G
from app.engine import intelligence as INT
from app.engine import roadmap as RM
from app.engine.catalog import get_catalog
from app.engine.knowledge import UserState, build_profile

CAT = get_catalog()
NOW = datetime(2026, 1, 15, tzinfo=timezone.utc)
DEMO = {"python": "intermediate", "sql": "intermediate", "pandas": "beginner", "numpy": "beginner",
        "statistics": "beginner", "machine-learning": "beginner", "git": "intermediate"}


def _attempt(score, days_ago=0, objective=True, key="q"):
    return {"id": hash((key, days_ago, score)) % 100000, "slug": "python", "key": key, "category": "mcq",
            "score": score, "objective": objective, "topic": "Sets", "missed_topics": [] if score >= 70 else ["Sets"],
            "correct": score >= 70, "created_at": NOW - timedelta(days=days_ago)}


def _cal(attempts, confidence=80.0, latest=NOW):
    return INT.calibrate("python", state=UserState(confidence_ratings={"python": confidence}),
                         estimate=None, attempts=attempts, available_objective=3,
                         latest_evidence_at=latest, now=NOW)


def _intelligence(role_name, state):
    estimates = build_profile(state)
    scores = {k: v.score for k, v in estimates.items()}
    role = CAT.roles[role_name]
    gap = G.analyze(CAT, role, scores, state.completed_roadmap)
    nodes = RM.build(CAT, gap, scores, state.completed_roadmap)
    return INT.build_intelligence(CAT, state=state, estimates=estimates, gap=gap, nodes=nodes,
                                  attempt_details=[], learning_events={}, schedules={}, evidence_dates={}, now=NOW)


# ---------------------------------------------------------------- bottleneck formula
def test_bottleneck_prefers_weak_foundations_with_important_downstream():
    st = UserState(self_levels={"python": "beginner", "statistics": "beginner", "machine-learning": "beginner",
                                "pandas": "beginner", "numpy": "beginner"})
    intel = _intelligence("Machine Learning Engineer", st)
    top = intel["top_bottleneck"]
    assert top is not None and top["downstream_count"] >= 2
    assert set(top["components"]) == {"weakness", "downstream_count", "downstream_importance", "current_stage"}
    assert 0 <= top["bottleneck_score"] <= 100 and top["why"] and top["action"]["route"].startswith("/learn?skill=")
    assert all(b["current_score"] < G.STRONG for b in intel["bottlenecks"])


def test_bottleneck_candidates_follow_the_selected_role():
    ml = _intelligence("Machine Learning Engineer",
                       UserState(self_levels={"python": "beginner", "statistics": "beginner"}))
    fs = _intelligence("Full Stack Developer",
                       UserState(self_levels={"javascript": "beginner", "html": "beginner", "css": "beginner"}))
    assert {b["slug"] for b in ml["bottlenecks"]} != {b["slug"] for b in fs["bottlenecks"]}
    assert "javascript" in {b["slug"] for b in fs["bottlenecks"]} or "html" in {b["slug"] for b in fs["bottlenecks"]}


def test_strong_prerequisites_are_not_bottlenecks():
    st = UserState(self_levels={r.slug: "expert" for r in CAT.roles["Machine Learning Engineer"].skills},
                   assessment={r.slug: 95 for r in CAT.roles["Machine Learning Engineer"].skills})
    assert _intelligence("Machine Learning Engineer", st)["bottlenecks"] == []


# ---------------------------------------------------------------- calibration formula
def test_calibration_states_and_insufficient_evidence():
    one = [_attempt(0)]
    assert _cal(one, 95)["status"] == "insufficient_evidence"          # one answer never labels confidence
    three_low = [_attempt(20, key=f"a{i}") for i in range(3)]
    assert _cal(three_low, 90)["status"] == "higher_than_demonstrated"
    three_high = [_attempt(90, key=f"b{i}") for i in range(3)]
    assert _cal(three_high, 20)["status"] == "lower_than_demonstrated"
    assert _cal(three_high, 85)["status"] == "aligned"
    stale = [_attempt(90, days_ago=200, key=f"c{i}") for i in range(3)]
    assert _cal(stale, 85)["status"] == "insufficient_evidence"      # old evidence needs a fresh check
    self_rated = [_attempt(100, objective=False, key=f"d{i}") for i in range(3)]
    assert _cal(self_rated, 85)["status"] == "insufficient_evidence"  # self-ratings are not demonstration


def test_one_answer_is_shrunk_for_the_knowledge_source():
    one = [_attempt(0)]
    assert INT.weighted_performance(one, NOW) == 0
    assert INT.weighted_performance(one, NOW, shrink=True) == 25      # informs, does not swing, the estimate


def test_calibration_reports_missed_topics_and_freshness():
    cal = _cal([_attempt(0, key=f"e{i}") for i in range(3)], 90)
    assert cal["missed_topics"] == ["Sets"] and cal["evidence_freshness"] == "fresh"
    assert cal["demonstrated_score"] == 0 and cal["self_rating"] == 90 and cal["difference"] == 90


# ---------------------------------------------------------------- recall scheduling
def test_recall_intervals_adapt_to_the_result():
    assert INT.next_stage_and_interval(0, 90)[:3] == (1, 3, "strong")
    assert INT.next_stage_and_interval(3, 60, 14)[:3] == (3, 7, "partial")
    assert INT.next_stage_and_interval(4, 10, 30)[:3] == (0, 1, "weak")


def test_learned_skill_without_evidence_is_a_diagnostic_not_forgotten():
    cal = _cal([], 50)
    entry = INT.review_entry("python", "Python", schedule=None, learned_at=NOW - timedelta(days=20),
                             calibration=cal, bottleneck=None, now=NOW)
    assert entry["status"] == "overdue" and entry["diagnostic"] is True
    assert "don't assume" in entry["reason"]


# ---------------------------------------------------------------- API helpers
def _setup(client, auth, role="Machine Learning Engineer", levels=DEMO, confidence=None):
    assert client.put("/roles/target", headers=auth, json={"name": role}).status_code == 200
    answers = [{"skill": s, "level": l, **({"confidence": confidence} if confidence is not None else {})}
               for s, l in levels.items()]
    r = client.post("/assessment", headers=auth, json={"answers": answers})
    assert r.status_code == 200, r.text
    return r.json()


def _run_check(client, auth, skill, purpose, correct):
    r = client.post("/interview/check/start", headers=auth, json={"skill": skill, "purpose": purpose, "count": 3})
    assert r.status_code == 200, r.text
    started = r.json()
    answers = []
    for item in started["questions"]:
        q = CAT.questions[item["key"]]
        if q.category == "mcq":
            answers.append({"question_key": q.key, "choice": q.answer_index if correct else (q.answer_index + 1) % len(q.options)})
        else:
            answers.append({"question_key": q.key, "answer": " ".join(q.keywords) if correct else "short"})
    r = client.post("/interview/check/submit", headers=auth,
                    json={"skill": skill, "purpose": purpose, "session_id": started["session_id"], "answers": answers})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- API integration
def test_self_confidence_is_saved_kept_separate_and_validated(client, auth):
    _setup(client, auth, confidence=90)
    form = client.get("/assessment", headers=auth).json()
    py = next(s for g in form["groups"] for s in g["skills"] if s["slug"] == "python")
    assert py["confidence_rating"] == 90
    assert py["calibration"]["self_rating"] == 90 and py["calibration"]["status"] == "insufficient_evidence"
    assert py["calibration"]["demonstrated_score"] is None
    assert client.post("/assessment", headers=auth,
                       json={"answers": [{"skill": "python", "confidence": 101}]}).status_code == 422
    assert client.post("/assessment", headers=auth,
                       json={"answers": [{"skill": "nope", "confidence": 10}]}).status_code == 422


def test_knowledge_check_updates_calibration_everywhere(client, auth):
    _setup(client, auth, confidence=90)
    result = _run_check(client, auth, "python", "calibration", correct=False)
    cal = result["intelligence"]["calibration"]
    assert result["score"] == 0 and result["total"] == 3 and result["weak_topics"]
    assert cal["status"] == "higher_than_demonstrated" and cal["demonstrated_score"] == 0
    graph = client.get("/skill-graph", headers=auth).json()
    node = next(n for n in graph["nodes"] if n["id"] == "python")
    assert node["calibration_status"] == "higher_than_demonstrated"
    dash = client.get("/dashboard", headers=auth).json()
    assert dash["intelligence"]["calibrations"]["python"]["status"] == "higher_than_demonstrated"
    assert dash["intelligence"]["top_bottleneck"] is not None
    # History is preserved: the knowledge check appended evidence instead of overwriting the estimate.
    assert node["intelligence"]["evidence_history"] and node["intelligence"]["evidence_history"][0]["source"] == "knowledge_check"


def test_learning_creates_a_review_and_strong_recall_spaces_it_out(client, auth):
    _setup(client, auth)
    r = client.put("/roadmap/statistics/complete", headers=auth, json={"completed": True})
    assert r.status_code == 200, r.text
    node = next(n for n in r.json()["nodes"] if n["slug"] == "statistics")
    assert node["status"] == "completed" and node["intelligence"]["review"]["status"] == "upcoming"
    due = client.get("/learn/recall/due", headers=auth).json()
    assert "statistics" in {x["slug"] for x in due["upcoming_reviews"]}

    result = _run_check(client, auth, "statistics", "recall", correct=True)
    assert result["score"] >= 80 and result["schedule"]["result"] == "strong"   # short open answers are capped by design
    assert result["schedule"]["interval_days"] == 3
    roadmap = client.get("/roadmap", headers=auth).json()
    node = next(n for n in roadmap["nodes"] if n["slug"] == "statistics")
    assert node["status"] == "completed"                       # a review never reopens the milestone
    assert node["intelligence"]["review"]["last_score"] == round(result["score"])


def test_weak_recall_shortens_the_cycle_without_erasing_completion(client, auth):
    _setup(client, auth)
    assert client.put("/learn/python/complete", headers=auth, json={"completed": True}).status_code == 200
    result = _run_check(client, auth, "python", "recall", correct=False)
    assert result["schedule"]["result"] == "weak" and result["schedule"]["interval_days"] == 1
    learn = client.get("/learn/python", headers=auth).json()
    assert learn["completed"] is True and learn["intelligence"]["review"]["weak_topics"]


def test_check_endpoints_validate_skill_questions_and_auth(client, auth):
    _setup(client, auth)
    assert client.post("/interview/check/start", json={"skill": "python"}).status_code == 401
    assert client.post("/interview/check/start", headers=auth, json={"skill": "nope"}).status_code == 404
    # Probability has no objectively scored question in the bank yet: say so instead of inventing one.
    assert client.post("/interview/check/start", headers=auth, json={"skill": "probability"}).status_code == 422
    assert client.post("/interview/check/start", headers=auth,
                       json={"skill": "sql", "purpose": "recall"}).status_code == 409  # not learned yet


def test_intelligence_is_private_to_each_user(client, auth):
    _setup(client, auth, confidence=90)
    _run_check(client, auth, "python", "calibration", correct=False)
    assert client.put("/learn/python/complete", headers=auth, json={"completed": True}).status_code == 200

    other = client.post("/auth/register", json={"full_name": "Other User", "email": "other@example.com",
                                                 "password": "Passw0rdOK", "confirm_password": "Passw0rdOK"})
    assert other.status_code == 201, other.text
    hb = {"Authorization": f"Bearer {other.json()['access_token']}"}
    _setup(client, hb, levels={**DEMO})
    due_b = client.get("/learn/recall/due", headers=hb).json()
    assert due_b["due_reviews"] == [] and due_b["upcoming_reviews"] == []
    form_b = client.get("/assessment", headers=hb).json()
    py_b = next(s for g in form_b["groups"] for s in g["skills"] if s["slug"] == "python")
    assert py_b["confidence_rating"] is None and py_b["calibration"]["objective_attempts"] == 0


# ---------------------------------------------------------------- migration
def test_migration_upgrades_an_old_database_without_losing_data():
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE users (id VARCHAR(36) PRIMARY KEY)"))
        c.execute(text("CREATE TABLE skills (id INTEGER PRIMARY KEY)"))
        c.execute(text("INSERT INTO users VALUES ('u1')"))
        c.execute(text("INSERT INTO skills VALUES (1)"))
        c.execute(text("CREATE TABLE user_skills (id INTEGER PRIMARY KEY, user_id VARCHAR(36), skill_id INTEGER, "
                       "score FLOAT, level VARCHAR(20), confidence FLOAT, created_at TIMESTAMP, updated_at TIMESTAMP)"))
        c.execute(text("CREATE TABLE user_skill_assessments (id INTEGER PRIMARY KEY, user_id VARCHAR(36), skill_id INTEGER, "
                       "self_level VARCHAR(20), checklist JSON, test_score FLOAT, created_at TIMESTAMP, updated_at TIMESTAMP)"))
        c.execute(text("CREATE TABLE interview_attempts (id INTEGER PRIMARY KEY, user_id VARCHAR(36), question_id INTEGER, "
                       "answer TEXT, score FLOAT, created_at TIMESTAMP, updated_at TIMESTAMP)"))
        c.execute(text("CREATE TABLE user_progress (id INTEGER PRIMARY KEY, user_id VARCHAR(36), skill_id INTEGER, "
                       "item_type VARCHAR(20), item_id INTEGER, completed BOOLEAN, created_at TIMESTAMP, updated_at TIMESTAMP)"))
        c.execute(text("INSERT INTO user_skill_assessments VALUES (1,'u1',1,'beginner','{\"Loops\": true}',NULL,'2024-01-01','2024-01-01')"))
        c.execute(text("INSERT INTO user_skill_assessments VALUES (2,'u1',1,'advanced',NULL,70,'2024-02-01','2024-02-01')"))
        c.execute(text("INSERT INTO user_progress VALUES (1,'u1',1,'resource',0,1,'2024-02-01','2024-02-02')"))
        c.execute(text("INSERT INTO interview_attempts VALUES (1,'u1',1,'x',50,'2024-02-01','2024-02-01')"))

    actions = migrate_intelligence(engine)
    assert actions and migrate_intelligence(engine) == []     # idempotent
    insp = inspect(engine)
    assert "skill_recall_schedules" in insp.get_table_names()
    assert "confidence_rating" in {c["name"] for c in insp.get_columns("user_skill_assessments")}
    assert "completed_at" in {c["name"] for c in insp.get_columns("user_progress")}
    with engine.connect() as c:
        rows = c.execute(text("SELECT self_level, checklist, test_score FROM user_skill_assessments")).all()
        assert len(rows) == 1 and rows[0][0] == "advanced" and rows[0][1] and rows[0][2] == 70  # merged, not lost
        assert c.execute(text("SELECT completed_at FROM user_progress")).scalar() is not None
        assert c.execute(text("SELECT purpose FROM interview_attempts")).scalar() == "interview"
    engine.dispose()
