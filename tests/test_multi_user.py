"""Multi-user isolation and per-user personalisation (docs/multi-user requirements §1-§20)."""
import uuid

import pytest

from app.core.config import Settings, get_settings
from tests.conftest import REGISTER

A_LEVELS = {"python": "intermediate", "numpy": "intermediate", "pandas": "intermediate", "statistics": "beginner", "sql": "intermediate", "git": "intermediate"}
B_LEVELS = {"javascript": "intermediate", "html": "intermediate", "css": "intermediate", "git": "intermediate", "sql": "beginner", "rest-apis": "beginner"}
C_LEVELS = {"python": "intermediate", "statistics": "intermediate", "machine-learning": "intermediate", "scikit-learn": "intermediate", "numpy": "intermediate", "pandas": "intermediate"}


def make_user(client, name, email, role, levels=None):
    body = {"full_name": name, "email": email, "password": "Passw0rd1", "confirm_password": "Passw0rd1"}
    tok = client.post("/auth/register", json=body).json()
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    if role:
        assert client.put("/roles/target", headers=h, json={"name": role}).status_code == 200
    if levels:
        r = client.post("/assessment", headers=h, json={"answers": [{"skill": s, "level": l} for s, l in levels.items()]})
        assert r.status_code == 200
    return tok["user"]["id"], h


@pytest.fixture()
def two(client):
    a = make_user(client, "Alice A", "a@example.com", "Machine Learning Engineer", A_LEVELS)
    b = make_user(client, "Bob B", "b@example.com", "Full Stack Developer", B_LEVELS)
    return a, b


# ---- §4: different users, different dashboards ----
def test_each_user_sees_their_own_dashboard(client, two):
    (ida, ha), (idb, hb) = two
    da, db = (client.get("/api/dashboard", headers=h).json() for h in (ha, hb))
    assert da["user"]["id"] == ida and db["user"]["id"] == idb
    assert da["user"]["name"] == "Alice A" and db["user"]["name"] == "Bob B"
    assert da["target_role"]["name"] == "Machine Learning Engineer" and db["target_role"]["name"] == "Full Stack Developer"
    assert da["recommended_next_skill"]["slug"] == "statistics" and db["recommended_next_skill"]["slug"] == "react"
    assert {s["slug"] for s in da["current_skills"]}.isdisjoint({"javascript", "html", "css"})
    assert {s["slug"] for s in db["current_skills"]}.isdisjoint({"python", "numpy", "pandas"})
    assert da["readiness_score"] != db["readiness_score"]


def test_gap_roadmap_and_recommendations_are_per_user(client, two):
    (_, ha), (_, hb) = two
    ga, gb = (client.get("/skill-gap", headers=h).json() for h in (ha, hb))
    assert ga["role"] != gb["role"] and {i["slug"] for i in ga["missing"]} != {i["slug"] for i in gb["missing"]}
    ra, rb = (client.get("/roadmap", headers=h).json() for h in (ha, hb))
    cur = lambda r: [n["slug"] for n in r["nodes"] if n["status"] == "current"]
    assert cur(ra) == ["statistics"] and cur(rb) == ["react"]
    na, nb = (client.get("/api/recommendations/next-skill", headers=h).json() for h in (ha, hb))
    assert na["slug"] != nb["slug"]


def test_same_role_different_progress_gives_different_roadmaps(client):
    _, ha = make_user(client, "Alice A", "a@example.com", "Machine Learning Engineer", A_LEVELS)
    _, hc = make_user(client, "Cara C", "c@example.com", "Machine Learning Engineer", C_LEVELS)
    state = lambda h: {n["slug"]: n["status"] for n in client.get("/roadmap", headers=h).json()["nodes"]}
    sa, sc = state(ha), state(hc)
    assert sa["machine-learning"] == "locked" and sc["machine-learning"] == "completed"
    assert [k for k, v in sa.items() if v == "current"] != [k for k, v in sc.items() if v == "current"]


# ---- §14/§15: identity comes only from the token ----
def test_user_id_parameter_is_ignored(client, two):
    (ida, ha), (idb, hb) = two
    for path in ("/api/dashboard", "/dashboard", "/profile", "/skill-gap", "/roadmap", "/progress", "/resume", "/api/profile"):
        mine = client.get(path, headers=ha).json()
        spoof = client.get(f"{path}?user_id={idb}", headers=ha).json()
        assert spoof == mine, path
    assert client.get(f"/api/dashboard?user_id={idb}", headers=ha).json()["user"]["id"] == ida


def test_no_route_accepts_a_user_id(client):
    from app.main import app

    for r in app.routes:
        dep = getattr(r, "dependant", None)
        if dep is None:
            continue
        names = {p.name for p in dep.query_params + dep.path_params + dep.body_params + dep.header_params}
        assert "user_id" not in names, f"{r.path} accepts a user_id"


def test_forged_and_foreign_tokens(client, two):
    (ida, ha), (_, hb) = two
    import jwt

    forged = jwt.encode({"sub": ida, "jti": "x", "exp": 9999999999}, "wrong-secret", algorithm="HS256")
    assert client.get("/dashboard", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    unsigned = jwt.encode({"sub": ida, "exp": 9999999999}, key="", algorithm="none")
    assert client.get("/dashboard", headers={"Authorization": f"Bearer {unsigned}"}).status_code == 401
    assert client.get("/profile", headers=hb).json()["full_name"] == "Bob B"


def test_resumes_are_private(client, two):
    (_, ha), (_, hb) = two
    text = "Bob B\nbob@example.com | +91 98765 43210\n\nSKILLS\nJavaScript, React, Node.js\n\nPROJECTS\n- Built a shop app with React and Node.js serving 500 users\n"
    r = client.post("/resume/upload", headers=hb, files={"file": ("bob.txt", text.encode(), "text/plain")})
    assert r.status_code == 200 and any(s["slug"] == "react" for s in r.json()["pending"]["extracted"]["skills"])
    # Bob's STAGED resume is private too: Alice sees nothing and cannot confirm, discard or read it
    assert client.get("/resume", headers=ha).json() == {"uploaded": False, "pending": None}
    assert client.post("/resume/confirm", headers=ha, json={}).status_code == 404
    assert client.delete("/resume/pending", headers=ha).status_code == 204
    assert client.get("/resume", headers=hb).json()["pending"]["filename"] == "bob.txt", "Alice's discard must not touch Bob's"
    assert client.post("/resume/confirm", headers=hb, json={}).status_code == 200
    assert client.post("/resume/analyze", headers=ha).status_code == 404
    assert client.delete("/resume", headers=ha).status_code == 204
    assert client.get("/resume", headers=hb).json()["uploaded"] is True, "Alice's remove must not touch Bob's"
    da = client.get("/dashboard", headers=ha).json()
    assert "react" not in {s["slug"] for s in da["current_skills"]}
    assert client.get("/resume", headers=hb).json()["uploaded"] is True


def test_progress_activity_projects_and_interview_are_private(client, two):
    (_, ha), (_, hb) = two
    client.put("/roadmap/statistics/complete", headers=ha)
    client.put("/learn/react/complete", headers=hb)
    qs = client.post("/interview/start", headers=hb, json={"category": "mcq", "count": 2}).json()["questions"]
    client.post("/interview/answer", headers=hb, json={"question_key": qs[0]["key"], "choice": 0})
    client.post("/projects/portfolio-react/status", headers=hb, json={"status": "completed"})
    client.post("/certifications", headers=hb, json={"name": "React Cert", "skill": "react"})
    client.get("/search?q=kubernetes", headers=hb)

    ta = " ".join(x["text"] for x in client.get("/dashboard", headers=ha).json()["recent_activity"])
    tb = " ".join(x["text"] for x in client.get("/dashboard", headers=hb).json()["recent_activity"])
    assert "Statistics" in ta and "React" not in ta and "Kubernetes" not in ta and "interview" not in ta.lower()
    assert "Kubernetes" in tb and "Statistics" not in tb
    assert client.get("/certifications", headers=ha).json() == []
    assert client.get("/build", headers=ha).json()["mine"] == []
    assert client.get("/interview/readiness", headers=ha).json()["overall"] is None
    assert client.get("/progress", headers=ha).json()["interview_attempts"] == 0


def test_activity_endpoint_records_for_the_caller_only(client, two):
    (_, ha), (_, hb) = two
    assert client.post("/activity", headers=ha, json={"type": "resource_opened", "skill": "statistics", "url": "https://www.youtube.com/results?search_query=x"}).status_code == 201
    assert "Opened a learning resource for Statistics" in [x["text"] for x in client.get("/dashboard", headers=ha).json()["recent_activity"]]
    assert all("learning resource" not in x["text"] for x in client.get("/dashboard", headers=hb).json()["recent_activity"])
    assert client.post("/activity", headers=ha, json={"type": "login", "skill": "python"}).status_code == 422
    assert client.post("/activity", headers=ha, json={"type": "resource_opened", "skill": "nope"}).status_code == 404
    assert client.post("/activity", json={"type": "resource_opened", "skill": "python"}).status_code == 401


def test_photos_are_private(client, two):
    (_, ha), (_, hb) = two
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    assert client.post("/profile/photo", headers=ha, files={"file": ("a.png", png, "image/png")}).status_code == 200
    assert client.get("/profile/photo", headers=ha).status_code == 200
    assert client.get("/profile/photo", headers=hb).status_code == 404  # B has none, and can never be served A's
    assert client.get("/profile/photo").status_code == 401


def test_changing_role_updates_database_and_recalculates(client, two):
    (_, ha), _ = two
    before = client.get("/skill-gap", headers=ha).json()
    assert client.put("/roles/target", headers=ha, json={"name": "Data Scientist"}).status_code == 200
    assert client.get("/profile", headers=ha).json()["target_role"] == "Data Scientist"   # persisted, not client state
    after = client.get("/skill-gap", headers=ha).json()
    assert after["role"] == "Data Scientist" and after["readiness"] != before["readiness"]
    from app.main import app
    from app.core.database import get_db
    from app.models import Profile

    db = next(app.dependency_overrides[get_db]())
    assert db.query(Profile).filter(Profile.target_role_id.is_not(None)).count() >= 2


# ---- §16: first login shows no fake numbers ----
def test_brand_new_user_gets_onboarding_not_numbers(client, auth):
    d = client.get("/api/dashboard", headers=auth).json()
    assert d["user"]["name"] == "Rahul Kumar" and d["target_role"] is None and d["needs"] == "target_role"
    for k in ("readiness_score", "recommended_next_skill", "roadmap_progress"):
        assert d[k] is None
    for k in ("current_skills", "critical_gaps", "project_recommendations", "job_matches", "youtube_resources", "learning_recommendations"):
        assert d[k] == [], k
    steps = {s["key"]: s for s in d["onboarding"]["steps"]}
    assert steps["profile"]["status"] == "todo" and steps["target_role"]["status"] == "todo"
    assert steps["resume"]["status"] == "optional" and steps["assessment"]["status"] == "not_started" and d["onboarding"]["next"] == "profile"


def test_onboarding_progress_tracks_the_user(client, auth):
    client.put("/profile", headers=auth, json={"location": "Pune", "education_level": "bachelors", "experience_level": "fresher"})
    client.put("/roles/target", headers=auth, json={"name": "Machine Learning Engineer"})
    st = {s["key"]: s for s in client.get("/dashboard", headers=auth).json()["onboarding"]["steps"]}
    assert st["profile"]["status"] == "done" and st["target_role"]["status"] == "done" and st["knowledge"]["percent"] == 0
    client.post("/assessment", headers=auth, json={"answers": [{"skill": "python", "level": "intermediate"}]})
    d = client.get("/dashboard", headers=auth).json()
    st = {s["key"]: s for s in d["onboarding"]["steps"]}
    assert 0 < st["knowledge"]["percent"] < 25 and st["assessment"]["status"] == "in_progress" and d["needs"] == "assessment"
    assert d["readiness_score"] is None and d["critical_gaps"] == []
    client.post("/assessment", headers=auth, json={"answers": [{"skill": s, "level": "beginner"} for s in ("numpy", "pandas", "sql", "git", "statistics")]})
    d = client.get("/dashboard", headers=auth).json()
    assert d["needs"] is None and d["readiness_score"] is not None and d["onboarding"]["ready"] is True


def test_modules_withhold_numbers_until_there_is_enough_data(client, auth):
    client.put("/roles/target", headers=auth, json={"name": "Machine Learning Engineer"})
    client.post("/assessment", headers=auth, json={"answers": [{"skill": "python", "level": "advanced"}]})
    assert client.get("/skill-gap", headers=auth).json().keys() == {"needs", "role", "onboarding"}
    rm = client.get("/roadmap", headers=auth).json()
    assert rm["nodes"] == [] and rm["progress"] is None
    assert client.get("/jobs", headers=auth).json()["jobs"] == []
    assert client.get("/learn", headers=auth).json()["skills"] == []
    assert client.get("/projects/recommended", headers=auth).json() == []
    assert client.get("/recommendations", headers=auth).json()["next_skill"] is None
    assert client.get("/progress", headers=auth).json()["readiness"] is None


# ---- §1/§19: demo mode ----
def test_demo_mode_defaults_to_false():
    assert Settings.model_fields["DEMO_MODE"].default is False


def test_production_requires_a_real_secret():
    with pytest.raises(RuntimeError):
        Settings(DEMO_MODE=False, SECRET_KEY="change-me-in-env").assert_secure()
    with pytest.raises(RuntimeError):
        Settings(DEMO_MODE=False, SECRET_KEY="short").assert_secure()
    Settings(DEMO_MODE=False, SECRET_KEY="x" * 40).assert_secure()


def test_demo_accounts_are_inert_outside_demo_mode(client, monkeypatch):
    from app.main import app
    from app.core.database import get_db
    from app.core.security import hash_password
    from app.repositories import users as repo

    db = next(app.dependency_overrides[get_db]())
    u = repo.create_user_with_profile(db, full_name="Demo Person", email="demo@demo.skillgraph.ai", hashed_password=hash_password("DemoPass123"))
    u.is_demo_account = True
    db.commit()
    creds = {"email": "demo@demo.skillgraph.ai", "password": "DemoPass123"}
    s = get_settings()
    monkeypatch.setattr(s, "DEMO_MODE", True)
    ok = client.post("/auth/login", json=creds)
    assert ok.status_code == 200
    token = {"Authorization": f"Bearer {ok.json()['access_token']}"}
    monkeypatch.setattr(s, "DEMO_MODE", False)
    assert client.post("/auth/login", json=creds).status_code == 401
    assert client.get("/profile", headers=token).status_code == 401   # an existing token stops working too


def test_real_registration_never_creates_a_demo_account(client):
    from app.main import app
    from app.core.database import get_db
    from app.models import User

    client.post("/auth/register", json=REGISTER)
    db = next(app.dependency_overrides[get_db]())
    assert db.query(User).filter(User.is_demo_account.is_(True)).count() == 0


# ---- repository layer ----
def test_user_scope_enforces_ownership():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.models import Base, Certification, User
    from app.repositories.scoped import UserScope

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    db = sessionmaker(bind=eng)()
    ua, ub = str(uuid.uuid4()), str(uuid.uuid4())
    for uid, e in ((ua, "a@x.io"), (ub, "b@x.io")):
        db.add(User(id=uid, email=e, full_name="X Y", hashed_password="h"))
    db.commit()
    A, B = UserScope(db, ua), UserScope(db, ub)
    cert = Certification(name="Mine", user_id=ub)   # a caller trying to write under another id...
    A.add(cert)
    db.commit()
    assert cert.user_id == ua                         # ...is overridden: ownership is forced
    assert [c.name for c in A.all(Certification)] == ["Mine"] and B.all(Certification) == []
    assert B.first(Certification) is None and B.count(Certification) == 0
    B.delete_where(Certification)                    # cannot delete A's rows
    db.commit()
    assert A.count(Certification) == 1
    with pytest.raises(TypeError):
        A.all(User)                                   # global/non-owned tables are refused
    with pytest.raises(ValueError):
        UserScope(db, "")


def test_custom_role_names_do_not_leak_between_users(client, two):
    (_, ha), (_, hb) = two
    assert client.put("/roles/target", headers=ha, json={"name": "Secret Quantum Basket Role"}).status_code == 200
    seen = []
    for rid in range(1, 60):
        r = client.get(f"/roles/{rid}", headers=hb)
        if r.status_code == 200:
            seen.append(r.json()["name"])
    assert "Secret Quantum Basket Role" not in seen
    assert "Secret Quantum Basket Role" not in [r["name"] for r in client.get("/roles", headers=hb).json()]


# ---- dashboard intelligence: Next Best Action, blockers, network, journey (per user, from stored evidence) ----
def test_dashboard_intelligence_is_per_user(client, two):
    (_, ha), (_, hb) = two
    da, db = (client.get("/api/dashboard", headers=h).json() for h in (ha, hb))
    assert da["next_best_action"]["type"] == "learn" and da["next_best_action"]["skill"] == "statistics" and da["next_best_action"]["reason"]
    assert db["next_best_action"]["type"] == "project" and "Portfolio" in db["next_best_action"]["title"]
    for d in (da, db):
        b = d["readiness_blockers"]
        assert b["goal"] == 80 and b["current"] == d["readiness_score"] and b["blockers"]
        gains = [x["gain"] for x in b["blockers"] if x["gain"] is not None]
        assert gains == sorted(gains, reverse=True)
        net = d["skill_network"]
        ids = {n["id"] for n in net["nodes"]}
        assert all(e["source"] in ids and e["target"] in ids for e in net["edges"]) and net["nodes"]
    assert {n["id"] for n in da["skill_network"]["nodes"]} != {n["id"] for n in db["skill_network"]["nodes"]}
    assert [s["label"] for s in da["journey"]] == ["Profile", "Target role", "Skills assessed", "Roadmap started", "First project", "Interview practised"]
    assert sum(1 for s in da["journey"] if s["next"]) == 1
    ov = da["skill_overview"]
    assert {"strong", "developing", "critical"} == set(ov) and any(x["slug"] == "python" for x in ov["strong"])
    assert not {x["slug"] for x in ov["strong"]} & {x["slug"] for x in ov["critical"]}


def test_next_best_action_for_new_and_sparse_users(client, auth):
    d = client.get("/dashboard", headers=auth).json()
    assert d["next_best_action"]["type"] == "role" and d["next_best_action"]["route"] == "/role" and d["readiness_score"] is None
    assert "skill_network" not in d and "readiness_blockers" not in d          # no numbers until there is evidence
    client.put("/roles/target", headers=auth, json={"name": "Machine Learning Engineer"})
    n = client.get("/recommendations/next-best-action", headers=auth).json()
    assert n["type"] == "assessment" and n["route"] == "/assessment" and "Machine Learning Engineer" in n["reason"]


def test_next_best_action_endpoint_is_identity_only(client, two):
    (_, ha), (idb, hb) = two
    mine = client.get("/api/recommendations/next-best-action", headers=ha).json()
    assert client.get(f"/api/recommendations/next-best-action?user_id={idb}", headers=ha).json() == mine
    assert client.get("/recommendations/next-best-action").status_code == 401
    assert client.get("/recommendations/next-best-action", headers=hb).json() != mine


def test_verify_before_moving_on(client, two):
    (_, ha), _ = two
    for slug in ("numpy", "pandas", "statistics"):
        assert client.put(f"/roadmap/{slug}/complete", headers=ha).status_code == 200
    n = client.get("/recommendations/next-best-action", headers=ha).json()
    assert n["type"] == "verify" and "nothing proves it" in n["reason"] and n["route"] == "/interview"


# ---- skill graph endpoint and job application status ----
def test_skill_graph_is_per_user_with_evidence(client, two):
    (_, ha), (_, hb) = two
    ga, gb = (client.get("/api/skill-graph", headers=h).json() for h in (ha, hb))
    assert ga["role"] == "Machine Learning Engineer" and gb["role"] == "Full Stack Developer"
    assert {n["id"] for n in ga["nodes"]} != {n["id"] for n in gb["nodes"]}
    assert sum(ga["counts"].values()) == len(ga["nodes"]) and set(ga["counts"]) == {"acquired", "in_progress", "missing"}
    py = next(n for n in ga["nodes"] if n["id"] == "python")
    assert py["state"] == "acquired" and py["sources"] and py["verified"] is False   # self-assessed only: not verified
    assert next(n for n in ga["nodes"] if n["id"] == "statistics")["state"] == "in_progress"
    ml = next(n for n in ga["nodes"] if n["id"] == "machine-learning")
    assert ml["why"] and {p["slug"] for p in ml["prerequisites"]} == {"statistics", "numpy", "pandas"} and all({"slug", "name"} <= set(u) for u in ml["unlocks"])
    assert py["why"].startswith("Your evidence-based score is")
    assert all(e["source"] in {n["id"] for n in ga["nodes"]} for e in ga["edges"])
    assert client.get("/skill-graph").status_code == 401


def test_skill_graph_withholds_data_until_there_is_evidence(client, auth):
    client.put("/roles/target", headers=auth, json={"name": "Machine Learning Engineer"})
    g = client.get("/skill-graph", headers=auth).json()
    assert g["needs"] == "assessment" and "nodes" not in g and g["onboarding"]["steps"]


def test_job_application_status_is_private_and_visible(client, two):
    (_, ha), (_, hb) = two
    top = client.get("/jobs", headers=ha).json()["jobs"][0]
    assert top["application_status"] is None
    assert client.post(f"/jobs/{top['key']}/status", headers=ha, json={"status": "saved"}).status_code == 200
    assert next(j for j in client.get("/jobs", headers=ha).json()["jobs"] if j["key"] == top["key"])["application_status"] == "saved"
    assert client.get(f"/jobs/{top['key']}", headers=ha).json()["application_status"] == "saved"
    assert all(j["application_status"] is None for j in client.get("/jobs", headers=hb).json()["jobs"])   # Bob sees none of Alice's
    client.post(f"/jobs/{top['key']}/status", headers=ha, json={"status": "applied"})
    assert next(j for j in client.get("/jobs/recommended", headers=ha).json()["jobs"] if j["key"] == top["key"])["application_status"] in ("applied", None)


# ---- redesign data: projects page, job status removal, skill quiz, dashboard roadmap preview ----
def test_projects_endpoint_lists_every_project_with_the_users_status(client, two):
    (_, ha), (_, hb) = two
    r = client.get("/api/projects", headers=ha).json()
    assert r["is_demo_data"] is True and len(r["projects"]) >= 10
    keys = {p["key"] for p in r["projects"]}
    assert client.post("/projects/house-prices/status", headers=ha, json={"status": "completed"}).status_code == 200
    again = {p["key"]: p for p in client.get("/projects", headers=ha).json()["projects"]}
    assert set(again) == keys and again["house-prices"]["status"] == "completed" and again["house-prices"]["recommended"] in (True, False)
    other = {p["key"]: p for p in client.get("/projects", headers=hb).json()["projects"]}
    assert other["house-prices"]["status"] == "not_started"                       # Bob never sees Alice's progress
    first = client.get("/projects", headers=ha).json()["projects"][0]
    assert {"ready", "missing_slugs", "why", "relevance", "recommended", "description", "expected_output"} <= set(first)
    assert client.get("/projects").status_code == 401


def test_projects_endpoint_withholds_data_until_there_is_evidence(client, auth):
    client.put("/roles/target", headers=auth, json={"name": "Machine Learning Engineer"})
    r = client.get("/projects", headers=auth).json()
    assert r["needs"] == "assessment" and r["projects"] == []


def test_saved_jobs_can_be_removed_and_stay_private(client, two):
    (_, ha), (_, hb) = two
    key = client.get("/jobs", headers=ha).json()["jobs"][0]["key"]
    assert client.post(f"/jobs/{key}/status", headers=ha, json={"status": "saved"}).status_code == 200
    assert client.post(f"/jobs/{key}/status", headers=hb, json={"status": "saved"}).status_code == 200
    assert client.delete(f"/jobs/{key}/status", headers=ha).status_code == 204
    st = lambda h: next(j for j in client.get("/jobs", headers=h).json()["jobs"] if j["key"] == key)["application_status"]
    assert st(ha) is None and st(hb) == "saved", "removing Alice's saved job must not touch Bob's"
    assert client.delete(f"/jobs/{key}/status").status_code == 401 and client.delete("/jobs/nope/status", headers=ha).status_code == 404


def test_quiz_on_a_specific_skill(client, two):
    (_, ha), _ = two
    r = client.post("/interview/start", headers=ha, json={"skill": "statistics", "category": "mcq", "count": 5}).json()
    assert "Statistics" in r["based_on"] and r["questions"] and all(q["skill"] == "Statistics" for q in r["questions"] if q["skill"])
    assert client.post("/interview/start", headers=ha, json={"skill": "not-a-skill"}).status_code == 404


def test_dashboard_has_roadmap_preview_and_job_status(client, two):
    (_, ha), _ = two
    key = client.get("/jobs", headers=ha).json()["jobs"][0]["key"]
    client.post(f"/jobs/{key}/status", headers=ha, json={"status": "saved"})
    d = client.get("/api/dashboard", headers=ha).json()
    rp = d["roadmap_preview"]
    assert 1 <= len(rp) <= 4 and all(x["status"] in ("current", "available", "locked") for x in rp) and rp[0]["status"] == "current"
    assert all("application_status" in j for j in d["job_matches"])
