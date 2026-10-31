from app.core.config import get_settings
from tests.conftest import REGISTER


def test_register_creates_user_and_profile(client):
    r = client.post("/auth/register", json=REGISTER)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "rahul@example.com"
    assert "password" not in str(body).lower().replace("confirm", "")
    # profile exists immediately (spec §5)
    p = client.get("/profile", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert p.status_code == 200
    assert p.json()["profile_complete"] is False


def test_email_is_case_insensitive_and_unique(client):
    client.post("/auth/register", json=REGISTER)
    r = client.post("/auth/register", json={**REGISTER, "email": "RAHUL@Example.com"})
    assert r.status_code == 409


def test_password_rules(client):
    for pw in ["short1", "alllettersnodigit", "12345678901"]:
        r = client.post("/auth/register", json={**REGISTER, "password": pw, "confirm_password": pw})
        assert r.status_code == 422, pw


def test_password_mismatch(client):
    r = client.post("/auth/register", json={**REGISTER, "confirm_password": "Different1"})
    assert r.status_code == 422


def test_invalid_email(client):
    assert client.post("/auth/register", json={**REGISTER, "email": "nope"}).status_code == 422


def test_password_is_hashed(client, registered):
    from app.main import app
    from app.core.database import get_db
    from app.models import User

    db = next(app.dependency_overrides[get_db]())
    u = db.query(User).one()
    assert u.hashed_password != REGISTER["password"]
    assert u.hashed_password.startswith("$2")


def test_login_ok_and_wrong_password(client, registered):
    ok = client.post("/auth/login", json={"email": "rahul@example.com", "password": "Passw0rdOK"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/auth/login", json={"email": "rahul@example.com", "password": "wrong"})
    assert bad.status_code == 401
    unknown = client.post("/auth/login", json={"email": "who@example.com", "password": "Passw0rdOK"})
    assert unknown.status_code == 401
    # same message either way: no account enumeration
    assert bad.json()["detail"] == unknown.json()["detail"]


def test_protected_routes_require_token(client):
    assert client.get("/profile").status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/profile", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me(client, auth):
    r = client.get("/auth/me", headers=auth)
    assert r.status_code == 200 and r.json()["full_name"] == "Rahul Kumar"


def test_logout_revokes_token(client, auth):
    assert client.post("/auth/logout", headers=auth).status_code == 204
    assert client.get("/profile", headers=auth).status_code == 401


def test_login_accepts_email_with_spaces_and_capitals(client, registered):
    # Regression: addresses are copy-pasted/autofilled ("  Preview@Example.COM "). The old
    # after-validator lower-cased but never stripped, and ran after EmailStr had already
    # rejected the padded value, so a correct password still "couldn't log in".
    r = client.post("/auth/login", json={"email": "  RAHUL@Example.com  ", "password": "Passw0rdOK"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_auth_accepts_fallback_header_when_authorization_is_unusable(client, registered):
    # Regression (real preview session): POST /auth/login -> 200, then GET /dashboard+/profile
    # -> 401, bouncing the browser back to /login -- the Authorization header was unusable on
    # the follow-up requests in that proxied path, while the same flow worked locally. The app
    # now also sends X-Auth-Token and the backend accepts the first credential that verifies.
    token = registered["access_token"]
    assert client.get("/profile", headers={"X-Auth-Token": token}).status_code == 200
    clobbered = {"Authorization": "Bearer not-the-app-token", "X-Auth-Token": token}
    assert client.get("/profile", headers=clobbered).status_code == 200
    assert client.get("/dashboard", headers=clobbered).status_code == 200
    # ...but garbage everywhere (or nothing) is still rejected.
    assert client.get("/profile", headers={"Authorization": "Bearer no", "X-Auth-Token": "no"}).status_code == 401
    assert client.get("/profile").status_code == 401


def test_rate_limit_buckets_are_per_forwarded_client(client, monkeypatch):
    # Regression: behind the Vite/reverse proxy every visitor arrives as 127.0.0.1, so keying
    # the limiter on request.client.host put all users in ONE bucket. Each X-Forwarded-For
    # client must get its own bucket.
    s = get_settings()
    monkeypatch.setattr(s, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(s, "AUTH_RATE_LIMIT", 3)
    one = {"x-forwarded-for": "203.0.113.1"}
    codes = [client.post("/auth/login", json={"email": "a@b.co", "password": "x"}, headers=one).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    other = client.post("/auth/login", json={"email": "a@b.co", "password": "x"}, headers={"x-forwarded-for": "203.0.113.2"})
    assert other.status_code == 401  # a different forwarded client is not locked out


def test_rate_limit(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(s, "AUTH_RATE_LIMIT", 3)
    codes = [client.post("/auth/login", json={"email": "a@b.co", "password": "x"}).status_code for _ in range(5)]
    assert codes[:3] == [401, 401, 401]
    assert codes[3:] == [429, 429]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_user_ids_are_uuid4(client):
    import uuid

    a = client.post("/auth/register", json=REGISTER).json()["user"]["id"]
    b = client.post("/auth/register", json={**REGISTER, "email": "b@example.com"}).json()["user"]["id"]
    assert a != b and uuid.UUID(a).version == 4 and uuid.UUID(b).version == 4
