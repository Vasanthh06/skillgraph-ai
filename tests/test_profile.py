PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_update_and_read_back(client, auth):
    r = client.put(
        "/profile",
        headers=auth,
        json={
            "location": "Bengaluru",
            "education_level": "bachelors",
            "experience_level": "fresher",
            "target_role": "Machine Learning Engineer",
            "graduation_year": 2025,
            "github_url": "https://github.com/rahul",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile_complete"] is True and body["missing_fields"] == []
    assert body["target_role"] == "Machine Learning Engineer"
    assert client.get("/profile", headers=auth).json()["location"] == "Bengaluru"


def test_partial_update_keeps_other_fields(client, auth):
    client.put("/profile", headers=auth, json={"location": "Pune"})
    client.put("/profile", headers=auth, json={"degree": "B.Tech"})
    body = client.get("/profile", headers=auth).json()
    assert body["location"] == "Pune" and body["degree"] == "B.Tech"


def test_missing_fields_reported(client, auth):
    body = client.get("/profile", headers=auth).json()
    assert set(body["missing_fields"]) == {"Location", "Education level", "Experience", "Target role"}


def test_can_change_name(client, auth):
    r = client.put("/profile", headers=auth, json={"full_name": "  Rahul   K  "})
    assert r.json()["full_name"] == "Rahul K"


def test_custom_target_role_allowed(client, auth):
    r = client.put("/profile", headers=auth, json={"target_role": "Quantum Software Engineer"})
    assert r.json()["target_role"] == "Quantum Software Engineer"


def test_validation(client, auth):
    assert client.put("/profile", headers=auth, json={"github_url": "javascript:alert(1)"}).status_code == 422
    assert client.put("/profile", headers=auth, json={"experience_level": "ten years"}).status_code == 422
    assert client.put("/profile", headers=auth, json={"graduation_year": 1800}).status_code == 422
    assert client.put("/profile", headers=auth, json={"phone": "call me"}).status_code == 422


def test_photo_upload_ok(client, auth):
    r = client.post("/profile/photo", headers=auth, files={"file": ("me.png", PNG, "image/png")})
    assert r.status_code == 200
    url = r.json()["photo_url"]
    assert url == "/profile/photo"                         # no public file path is ever exposed
    got = client.get(url, headers=auth)
    assert got.status_code == 200 and got.content == PNG and got.headers["content-type"] == "image/png"
    assert "no-store" in got.headers["cache-control"]
    assert client.get(url).status_code == 401              # not publicly readable
    assert client.get("/uploads/photos/anything.png").status_code == 404  # and there is no public mount


def test_photo_rejects_non_image_even_with_image_name(client, auth):
    r = client.post("/profile/photo", headers=auth, files={"file": ("me.png", b"<?php echo 1;", "image/png")})
    assert r.status_code == 415


def test_photo_rejects_oversize(client, auth):
    big = PNG + b"\x00" * (2 * 1024 * 1024)
    r = client.post("/profile/photo", headers=auth, files={"file": ("me.png", big, "image/png")})
    assert r.status_code == 413


def test_photo_requires_auth(client):
    assert client.post("/profile/photo", files={"file": ("me.png", PNG, "image/png")}).status_code == 401


def test_users_cannot_see_each_others_profile(client, auth):
    client.put("/profile", headers=auth, json={"location": "Secretville"})
    other = client.post(
        "/auth/register",
        json={"full_name": "Other Person", "email": "o@example.com", "password": "Passw0rd1", "confirm_password": "Passw0rd1"},
    ).json()
    h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get("/profile", headers=h).json()["location"] is None


def test_schema_has_all_spec_tables():
    from app.models import Base

    expected = {
        "users", "profiles", "roles", "role_skills", "skills", "skill_aliases", "skill_dependencies",
        "skill_taxonomy", "user_skills", "user_skill_assessments", "resumes", "resume_skills", "jobs",
        "job_skills", "projects", "project_skills", "learning_resources", "resource_skills",
        "youtube_resources", "roadmaps", "roadmap_items", "user_progress", "user_projects", "applications",
        "interview_questions", "interview_attempts", "skill_embeddings", "user_embeddings", "search_history",
        "user_activity", "recommendations", "evidence", "certifications",
    }
    assert expected <= set(Base.metadata.tables)
