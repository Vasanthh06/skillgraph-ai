"""End-to-end API tests for Phases 2-12. Require the backend dependencies (see requirements.txt)."""
import io

H = lambda auth: auth  # readability alias

RESUME = (
    "Rahul Kumar\nrahul@example.com | +91 98765 43210\n\nSKILLS\nPython, SQL, Pandas, NumPy, Git\n\n"
    "PROJECTS\n- Built a churn model with Python, pandas and scikit-learn reaching 0.82 AUC on 7,000 rows\n"
    "- Responsible for data cleaning in a team project\n\nEDUCATION\nB.Tech in Computer Science\n"
)


def set_role(client, auth, name="Machine Learning Engineer"):
    r = client.put("/roles/target", headers=auth, json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()


def answer(client, auth, levels):
    body = {"answers": [{"skill": s, "level": l} for s, l in levels.items()]}
    r = client.post("/assessment", headers=auth, json=body)
    assert r.status_code == 200, r.text
    return r.json()


DEMO = {"python": "intermediate", "sql": "intermediate", "pandas": "beginner", "numpy": "beginner",
        "statistics": "beginner", "machine-learning": "beginner", "git": "intermediate"}


# ---- roles ----
def test_roles_listing_and_detail(client, auth):
    roles = client.get("/roles", headers=auth).json()
    assert len(roles) >= 8 and all(r["id"] for r in roles)
    ml = next(r for r in roles if r["name"] == "Machine Learning Engineer")
    d = client.get(f"/roles/{ml['id']}").json()
    assert d["required"] and d["skills"][0]["group"] and d["interview_topics"]
    assert [r["name"] for r in client.get("/roles?q=cloud").json()] == ["Cloud Engineer"]
    assert client.get("/roles/99999").status_code == 404


def test_custom_role_is_labelled_generated(client, auth):
    r = set_role(client, auth, "Applied Machine Learning Researcher")
    assert r["is_generated"] is True and r["derived_from"]


# ---- dashboard states ----
def test_dashboard_before_anything_has_no_fake_numbers(client, auth):
    d = client.get("/api/dashboard", headers=auth).json()
    assert d["readiness_score"] is None and d["needs"] == "target_role" and d["recommended_next_skill"] is None
    assert d["five_questions"]["where_to_go"]["answered"] is False


def test_dashboard_with_role_but_no_assessment(client, auth):
    set_role(client, auth)
    d = client.get("/dashboard", headers=auth).json()
    assert d["needs"] == "assessment" and d["readiness_score"] is None and d["target_role"]["name"] == "Machine Learning Engineer"
    assert d["onboarding"]["steps"] and d["job_matches"] == [] and d["critical_gaps"] == []


# ---- assessment -> gap -> dashboard (the central flow) ----
def test_full_personalisation_flow(client, auth):
    set_role(client, auth)
    form = client.get("/assessment", headers=auth).json()
    names = [g["name"] for g in form["groups"]]
    assert "Mathematics" in names and "Deep Learning" in names and len(form["levels"]) == 6
    res = answer(client, auth, DEMO)
    assert res["saved"] == 7 and res["readiness"]["overall"] > 0

    gap = client.get("/skill-gap", headers=auth).json()
    status = {i["slug"]: i["status"] for g in ("strong", "weak", "missing") for i in gap[g]}
    assert status["python"] == "strong" and status["pandas"] == "weak" and status["pytorch"] == "missing"
    order = [i["slug"] for i in gap["learn_next"]]
    assert order.index("machine-learning") < order.index("deep-learning")

    d = client.get("/api/dashboard", headers=auth).json()
    assert d["needs"] is None and d["readiness_score"] == gap["readiness"]["overall"]
    for k in ("user", "target_role", "current_skills", "critical_gaps", "recommended_next_skill", "roadmap_progress",
              "learning_recommendations", "youtube_resources", "project_recommendations", "job_matches", "interview_readiness", "recent_activity"):
        assert k in d
    nxt = d["recommended_next_skill"]
    assert nxt and all(nxt[k] for k in ("what", "why", "why_now", "impact", "next"))
    assert d["youtube_resources"] and all(v["url"].startswith("https://www.youtube.com/") for v in d["youtube_resources"])
    assert d["data_labels"]["jobs"] == "demo"


def test_assessment_validation(client, auth):
    set_role(client, auth)
    assert client.post("/assessment", headers=auth, json={"answers": [{"skill": "nonsense-skill", "level": "advanced"}]}).status_code == 422
    assert client.post("/assessment", headers=auth, json={"answers": [{"skill": "python", "level": "godlike"}]}).status_code == 422
    assert client.post("/assessment", headers=auth, json={"answers": [{"skill": "python", "checklist": {"Not an item": True}}]}).status_code == 422


def test_checkbox_alone_cannot_make_expert(client, auth):
    set_role(client, auth)
    answer(client, auth, {**DEMO, "python": "expert"})
    gap = client.get("/skill-gap", headers=auth).json()
    py = next(i for i in gap["strong"] if i["slug"] == "python")
    assert py["score"] <= 60


def test_checklist_assessment(client, auth):
    set_role(client, auth)
    leaves = [c["label"] for g in client.get("/assessment", headers=auth).json()["groups"] for s in g["skills"] if s["slug"] == "python" for c in s["checklist"]]
    assert leaves
    r = client.post("/assessment", headers=auth, json={"answers": [{"skill": "python", "checklist": {l: True for l in leaves}}]})
    assert r.status_code == 200


# ---- roadmap ----
def test_roadmap_unlocks_when_prereqs_complete(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    rm = client.get("/roadmap", headers=auth).json()
    st = {n["slug"]: n["status"] for n in rm["nodes"]}
    assert st["machine-learning"] == "locked" and sum(1 for s in st.values() if s == "current") == 1
    assert client.put("/roadmap/machine-learning/complete", headers=auth).status_code == 409  # locked

    for s in ("numpy", "pandas", "statistics"):
        r = client.put(f"/roadmap/{s}/complete", headers=auth)
        assert r.status_code == 200, r.text
    st = {n["slug"]: n["status"] for n in client.get("/roadmap", headers=auth).json()["nodes"]}
    assert st["machine-learning"] == "current"
    assert client.put("/roadmap/machine-learning/complete", headers=auth).status_code == 200
    st = {n["slug"]: n["status"] for n in client.get("/roadmap", headers=auth).json()["nodes"]}
    assert st["scikit-learn"] in ("current", "available")
    assert client.get("/progress", headers=auth).json()["roadmap"]["completed"] >= 4
    assert client.put("/roadmap/not-a-skill/complete", headers=auth).status_code == 404


def test_progress_updates_dashboard_and_readiness(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    before = client.get("/dashboard", headers=auth).json()["readiness_score"]
    for s in ("numpy", "pandas", "statistics"):
        client.put(f"/roadmap/{s}/complete", headers=auth)
    after = client.get("/dashboard", headers=auth).json()
    assert after["readiness_score"] > before
    assert any("Completed" in a["text"] for a in after["recent_activity"])


def test_roadmap_generate_persists(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    assert client.post("/roadmap/generate", headers=auth).json()["nodes"]


def test_target_role_change_keeps_skills_and_recalculates(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    ml = client.get("/skill-gap", headers=auth).json()
    set_role(client, auth, "Data Scientist")
    ds = client.get("/skill-gap", headers=auth).json()
    assert ds["role"] == "Data Scientist" and ds["readiness"] != ml["readiness"]
    py = lambda g: next(i for i in g["strong"] if i["slug"] == "python")["score"]
    assert py(ml) == py(ds)
    assert client.get("/roadmap", headers=auth).json()["role"] == "Data Scientist"


# ---- resume ----
def upload(client, auth, text=RESUME, name="cv.txt"):
    """Stage a resume. It is NOT part of the profile until confirmed."""
    return client.post("/resume/upload", headers=auth, files={"file": (name, text.encode(), "text/plain")})


def save_resume(client, auth, text=RESUME, name="cv.txt", exclude=None):
    assert upload(client, auth, text, name).status_code == 200
    r = client.post("/resume/confirm", headers=auth, json={"exclude": exclude or []})
    assert r.status_code == 200, r.text
    return r.json()


def test_resume_upload_extracts_and_normalises(client, auth):
    set_role(client, auth)
    # Only the SKILLS line: str.replace without a count would also rewrite the PROJECTS bullet
    # ("with Python, pandas ..."), putting ReactJS in applied text and making its evidence "applied".
    r = upload(client, auth, RESUME.replace("Python,", "Python, ReactJS,", 1))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["uploaded"] is False, "an upload must not be saved until confirmed"
    pend = body["pending"]
    ext = {s["slug"]: s for s in pend["extracted"]["skills"]}
    assert ext["react"]["evidence"] == "listed" and ext["python"]["evidence"] == "applied"
    assert pend["analysis"]["role_match"] >= 0 and pend["analysis"]["tips"]
    assert any("Weak phrasing" in t for t in pend["analysis"]["tips"])


def test_resume_feeds_knowledge_without_assessment(client, auth):
    set_role(client, auth)
    upload(client, auth)
    assert client.get("/dashboard", headers=auth).json()["needs"] == "assessment"   # staged only: no effect yet
    save_resume(client, auth)
    d = client.get("/dashboard", headers=auth).json()
    assert d["needs"] is None and any(s["slug"] == "python" for s in d["current_skills"])


def test_resume_and_assessment_combine(client, auth):
    set_role(client, auth)
    save_resume(client, auth)
    answer(client, auth, {"python": "advanced"})
    py = next(s for s in client.get("/dashboard", headers=auth).json()["current_skills"] if s["slug"] == "python")
    assert set(py["sources"]) == {"resume", "self"}


def test_resume_rejections(client, auth):
    assert client.post("/resume/upload", headers=auth, files={"file": ("cv.exe", b"MZ" * 50, "application/octet-stream")}).status_code == 415
    assert upload(client, auth, "too short").status_code == 422
    assert upload(client, auth, "just some words " * 20).status_code == 422  # not a resume
    big = client.post("/resume/upload", headers=auth, files={"file": ("cv.txt", b"x" * (5 * 1024 * 1024 + 10), "text/plain")})
    assert big.status_code == 413
    assert client.get("/resume", headers=auth).json() == {"uploaded": False, "pending": None}
    assert client.post("/resume/analyze", headers=auth).status_code == 404


def test_staged_resume_is_a_draft_until_confirmed(client, auth):
    set_role(client, auth)
    before = client.get("/dashboard", headers=auth).json()
    r = upload(client, auth).json()
    assert r["pending"]["note"] and r["uploaded"] is False
    assert client.get("/dashboard", headers=auth).json()["needs"] == before["needs"] == "assessment"
    assert client.get("/resume", headers=auth).json()["pending"]["filename"] == "cv.txt"      # survives a reload
    saved = client.post("/resume/confirm", headers=auth, json={}).json()
    assert saved["uploaded"] is True and saved["pending"] is None
    assert client.post("/resume/confirm", headers=auth, json={}).status_code == 404            # nothing left to confirm


def test_confirm_drops_the_skills_the_user_rejected(client, auth):
    set_role(client, auth)
    # Add extra role skills too: excluding Git+Docker from the plain RESUME leaves 5/22 role skills
    # with evidence, below the 25% coverage gate, so the dashboard intentionally shows no scores
    # yet (see services.views.needs). With Statistics/Machine Learning included, 7 remain and the
    # dashboard assertion below tests exclusion rather than the onboarding gate.
    saved = save_resume(client, auth, RESUME.replace("Git", "Git, Docker, Statistics, Machine Learning"), exclude=["docker", "git"])
    slugs = {s["slug"] for s in saved["extracted"]["skills"]}
    d = client.get("/dashboard", headers=auth).json()
    got = {s["slug"] for s in d["current_skills"]}
    assert "python" in got and "docker" not in got and "git" not in got
    assert client.post("/resume/confirm", headers=auth, json={"exclude": ["nonsense-skill"]}).status_code == 404  # nothing pending
    upload(client, auth)
    assert client.post("/resume/confirm", headers=auth, json={"exclude": ["nonsense-skill"]}).status_code == 422
    # The saved view lists the evidence that was actually kept: skills the user rejected at
    # confirm time must not reappear just because they are still in the resume's raw text.
    assert slugs and "python" in slugs and "docker" not in slugs and "git" not in slugs


def test_discard_pending_and_replace_pending(client, auth):
    set_role(client, auth)
    upload(client, auth, name="first.txt")
    upload(client, auth, name="second.txt")                                  # replaces the unreviewed one
    assert client.get("/resume", headers=auth).json()["pending"]["filename"] == "second.txt"
    assert client.delete("/resume/pending", headers=auth).status_code == 204
    assert client.get("/resume", headers=auth).json() == {"uploaded": False, "pending": None}
    assert client.post("/resume/confirm", headers=auth, json={}).status_code == 404


def test_new_upload_does_not_replace_the_saved_resume_until_confirmed(client, auth):
    set_role(client, auth)
    save_resume(client, auth, name="saved.txt")
    upload(client, auth, "Zed\nzed@x.io | +91 98765 43210\n\nSKILLS\nKubernetes, Terraform\n\nPROJECTS\n- Built infrastructure with Terraform on AWS for 3 services\n", "new.txt")
    r = client.get("/resume", headers=auth).json()
    assert r["filename"] == "saved.txt" and r["pending"]["filename"] == "new.txt"
    assert not any(s["slug"] == "kubernetes" for s in client.get("/dashboard", headers=auth).json()["current_skills"])


def test_removing_the_saved_resume_recalculates(client, auth):
    set_role(client, auth)
    save_resume(client, auth)
    assert client.get("/dashboard", headers=auth).json()["needs"] is None
    assert client.delete("/resume", headers=auth).status_code == 204
    assert client.get("/resume", headers=auth).json() == {"uploaded": False, "pending": None}
    assert client.get("/dashboard", headers=auth).json()["needs"] == "assessment"


def test_resume_requires_auth(client):
    assert client.post("/resume/upload", files={"file": ("cv.txt", b"x" * 100, "text/plain")}).status_code == 401
    assert client.post("/resume/confirm", json={}).status_code == 401
    assert client.delete("/resume/pending").status_code == 401 and client.delete("/resume").status_code == 401


# ---- skills / search ----
def test_search_exact_and_taxonomy(client, auth):
    r = client.get("/search?q=ReactJS", headers=auth).json()
    assert r["exact"]["slug"] == "react" and [p["name"] for p in r["exact"]["learning_path"]][-1] == "React"
    assert r["exact"]["graph"]["edges"] and r["exact"]["career_paths"] is not None
    py = client.get("/search?q=python", headers=auth).json()["exact"]
    assert py["taxonomy"]["children"] and py["jobs"] and py["projects"]
    ml = client.get("/skills/machine-learning/taxonomy").json()
    assert ml["provenance"] == "verified"


def test_search_unknown_and_empty(client, auth):
    r = client.get("/search?q=quantum%20basket%20weaving", headers=auth).json()
    assert r["exact"] is None and r["can_generate"] is True
    assert client.get("/search?q=", headers=auth).status_code == 422
    g = client.post("/skills/generate-taxonomy", headers=auth, json={"query": "x"})
    assert g.status_code == 501 and "language model" in g.json()["detail"]
    assert client.get("/skills/nope").status_code in (401, 404)


def test_search_typos_give_related(client, auth):
    r = client.get("/search?q=machin%20learning", headers=auth).json()
    assert "machine-learning" in [x["slug"] for x in r["related"]]


def test_search_history_drives_intent(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    for q in ("python", "pandas", "numpy", "machine learning", "scikit-learn"):
        client.get(f"/search?q={q}", headers=auth)
    d = client.get("/dashboard", headers=auth).json()
    assert d["intent"] and d["intent"]["source"] == "heuristic"


# ---- learn & build ----
def test_learn_never_fabricates_video_urls(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    learn = client.get("/learn", headers=auth).json()
    assert learn["skills"]
    for s in learn["skills"]:
        for v in s["learn"]["videos"]:
            assert v["is_search_url"] is True and "youtube.com/results?search_query=" in v["url"]
        assert set(s) >= {"learn", "practice", "build", "prove"}


def test_resource_completion_raises_estimate(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    r = client.put("/learn/statistics/complete", headers=auth)
    assert r.status_code == 200 and r.json()["completed"] is True


def test_projects_personalised_and_status(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    recs = client.get("/projects/recommended", headers=auth).json()
    assert recs and all(p["is_demo"] for p in recs) and all(p["gains"] for p in recs)
    first = recs[0]
    assert client.post(f"/projects/{first['key']}/status", headers=auth, json={"status": "completed"}).status_code == 200
    assert first["key"] not in [p["key"] for p in client.get("/projects/recommended", headers=auth).json()]
    assert client.post("/projects/nope/status", headers=auth, json={"status": "planned"}).status_code == 404
    assert client.post(f"/projects/{first['key']}/status", headers=auth, json={"status": "bogus"}).status_code == 422
    assert client.get("/build", headers=auth).json()["mine"][0]["status"] == "completed"


def test_certifications(client, auth):
    set_role(client, auth)
    assert client.post("/certifications", headers=auth, json={"name": "ML Specialization", "skill": "machine-learning"}).status_code == 201
    assert client.get("/certifications", headers=auth).json()[0]["skill"] == "Machine Learning"
    assert client.post("/certifications", headers=auth, json={"name": "X", "skill": "machine-learning"}).status_code == 422


# ---- jobs ----
def test_jobs_personalised(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    res = client.get("/jobs", headers=auth).json()
    assert res["is_demo_data"] is True and res["jobs"]
    top = res["jobs"][0]
    assert top["match"] >= res["jobs"][-1]["match"] and top["explanation"] and "have" in top and top["is_demo"]
    assert all(j["match"] >= 50 for j in client.get("/jobs?min_match=50", headers=auth).json()["jobs"])
    assert client.get("/jobs/recommended", headers=auth).json()["jobs"]
    assert client.get(f"/jobs/{top['key']}", headers=auth).json()["key"] == top["key"]
    assert client.post(f"/jobs/{top['key']}/status", headers=auth, json={"status": "applied"}).status_code == 200
    assert client.get("/jobs/nope", headers=auth).status_code == 404


JD = "Machine Learning Engineer\n\nRequirements:\n- 2+ years with Python and SQL\n- PyTorch and Docker\n\nNice to have:\n- AWS and Kubernetes\n"


def test_jd_analysis_endpoint(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    r = client.post("/jobs/analyze", headers=auth, json={"text": JD}).json()
    assert "PyTorch" in r["missing"] and "Python" in r["strong"] and "AWS" in r["preferred_skills"]
    assert client.post("/jobs/analyze", headers=auth, json={"text": "We are a friendly company with free snacks and a nice office."}).status_code == 422
    assert client.post("/jobs/analyze", headers=auth, json={"text": "short"}).status_code == 422


# ---- interview ----
def test_interview_flow_and_readiness(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    assert client.get("/interview/readiness", headers=auth).json()["overall"] is None  # nothing practised yet
    qs = client.post("/interview/start", headers=auth, json={"category": "mcq", "count": 4}).json()["questions"]
    assert len(qs) == 4 and all("answer_index" not in q and "explanation" not in q for q in qs)
    r = client.post("/interview/answer", headers=auth, json={"question_key": qs[0]["key"], "choice": 0}).json()
    assert r["method"] == "exact" and "correct_index" in r and r["readiness"]["overall"] is not None
    assert client.post("/interview/answer", headers=auth, json={"question_key": qs[0]["key"]}).status_code == 422
    assert client.post("/interview/answer", headers=auth, json={"question_key": "nope", "choice": 0}).status_code == 404


def test_interview_open_and_self_rated(client, auth):
    set_role(client, auth)
    tq = client.post("/interview/start", headers=auth, json={"category": "technical", "count": 1}).json()["questions"][0]
    assert tq["scoring"] == "keyword_coverage"
    assert client.post("/interview/answer", headers=auth, json={"question_key": tq["key"], "answer": ""}).status_code == 422
    r = client.post("/interview/answer", headers=auth, json={"question_key": tq["key"], "answer": "short"}).json()
    assert r["score"] <= 40 and "not an expert" in r["note"]
    hq = client.post("/interview/start", headers=auth, json={"category": "hr", "count": 1}).json()["questions"][0]
    r = client.post("/interview/answer", headers=auth, json={"question_key": hq["key"], "self_rating": 4}).json()
    assert r["score"] == 80 and r["method"] == "self_rated"


def test_interview_from_job_and_jd(client, auth):
    set_role(client, auth)
    j = client.post("/interview/start", headers=auth, json={"job_key": "devops-2", "count": 3}).json()
    assert "listing" in j["based_on"]
    assert all(q["skill"] in ("Docker", "Git", "Linux", "CI/CD", None) for q in j["questions"][:2])
    d = client.post("/interview/start", headers=auth, json={"jd_text": "We need Docker and Kubernetes experience"}).json()
    assert d["questions"] and all(q["skill"] == "Docker" for q in d["questions"] if q["skill"])
    assert client.post("/interview/start", headers=auth, json={"jd_text": "nothing relevant at all"}).status_code == 422
    assert client.post("/interview/start", headers=auth, json={"job_key": "nope"}).status_code == 404


def test_struggling_triggers_prerequisite_advice(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    for _ in range(3):
        qs = client.post("/interview/start", headers=auth, json={"category": "mcq", "count": 15}).json()["questions"]
        for q in qs:
            if q["skill"] == "Machine Learning":
                client.post("/interview/answer", headers=auth, json={"question_key": q["key"], "choice": 3})
    ov = client.get("/interview", headers=auth).json()
    assert ov["readiness"]["attempts"] > 0 and ov["is_demo_content"] is True


# ---- recommendations ----
def test_recommendations_explainable_and_honest_about_models(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    r = client.get("/recommendations", headers=auth).json()
    assert r["source"] == "rules" and r["next_skill"]["why"] and "not trained" in r["model_status"]["two_tower"]
    assert r["projects"] and r["jobs"] and r["interview_topics"]
    assert client.get("/recommendations/next-skill", headers=auth).json()["slug"] == r["next_skill"]["slug"]


def test_all_module_endpoints_require_auth(client):
    for path in ("/dashboard", "/api/dashboard", "/skill-gap", "/roadmap", "/learn", "/build", "/projects", "/jobs", "/interview",
                 "/resume", "/recommendations", "/progress", "/assessment", "/search?q=python", "/certifications",
                 "/api/profile", "/api/skill-gap", "/api/roadmap", "/api/recommendations", "/api/progress", "/api/jobs", "/api/learn"):
        assert client.get(path).status_code == 401, path


def test_users_are_isolated(client, auth):
    set_role(client, auth)
    answer(client, auth, DEMO)
    other = client.post("/auth/register", json={"full_name": "Other Person", "email": "o@example.com", "password": "Passw0rd1", "confirm_password": "Passw0rd1"}).json()
    h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get("/dashboard", headers=h).json()["readiness_score"] is None
