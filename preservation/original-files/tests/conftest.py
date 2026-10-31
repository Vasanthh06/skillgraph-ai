import os
import tempfile

# Must be set before the app is imported.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["DEMO_MODE"] = "true"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="sg-uploads-")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base
from app.utils.rate_limit import reset_rate_limits


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    reset_rate_limits()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


REGISTER = {
    "full_name": "Rahul Kumar",
    "email": "rahul@example.com",
    "password": "Passw0rdOK",
    "confirm_password": "Passw0rdOK",
}


@pytest.fixture()
def registered(client):
    r = client.post("/auth/register", json=REGISTER)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def auth(registered):
    return {"Authorization": f"Bearer {registered['access_token']}"}
