import hashlib
from datetime import datetime, timedelta, timezone
import bcrypt
import pytest
from app.main import app
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import verify_password, hash_password
from app.models import User
from app.models.account import AccountToken, AccountSecurity
from app.services import email_service
from tests.conftest import REGISTER

WEB = {"X-Requested-With": "SkillGraph"}

def db_session():
    return next(app.dependency_overrides[get_db]())


def test_web_cookie_csrf_refresh_logout(client):
    r = client.post('/auth/register', json=REGISTER, headers=WEB)
    assert r.status_code == 201
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=lax' in r.headers['set-cookie']
    assert client.get('/auth/me').status_code == 200
    assert client.post('/auth/logout').status_code == 403
    assert client.post('/auth/logout', headers=WEB).status_code == 204
    assert client.get('/auth/me').status_code == 401


def test_normal_user_cannot_admin(client, auth):
    assert client.get('/admin/users', headers=auth).status_code == 403


def test_admin_is_server_authorized(client, auth, registered):
    db = db_session()
    sec = db.get(AccountSecurity, registered['user']['id'])
    sec.is_admin = True
    db.commit()
    r = client.get('/admin/users?limit=1', headers=auth)
    assert r.status_code == 200 and len(r.json()['users']) == 1
    assert 'hashed_password' not in r.text and 'digest' not in r.text


def test_password_hash_backward_compatibility():
    pw = 'a very long passphrase with spaces'
    assert verify_password(pw, hash_password(pw))
    old = bcrypt.hashpw(b'OldPass123', bcrypt.gensalt()).decode()
    assert verify_password('OldPass123', old)
    assert not verify_password('wrong', old)


def test_adult_and_password_policy(client, monkeypatch):
    monkeypatch.setattr(get_settings(), 'DEMO_MODE', False)
    body = {**REGISTER, 'password': 'a sufficiently long passphrase', 'confirm_password': 'a sufficiently long passphrase'}
    assert client.post('/auth/register', json=body).status_code == 422
    body.update(adult_eligible=True, terms_accepted=True)
    assert client.post('/auth/register', json=body).status_code == 201


def test_forgot_generic_and_no_token_response(client, registered, monkeypatch):
    monkeypatch.setattr(email_service, 'send_email', lambda *args: 'mock-provider-id')
    a = client.post('/auth/forgot-password', json={'email': REGISTER['email']})
    b = client.post('/auth/forgot-password', json={'email': 'unknown@example.com'})
    assert a.json() == b.json() and 'token' not in a.text
    db = db_session()
    assert len(db.query(AccountToken).one().digest) == 64


@pytest.mark.parametrize('expired,used', [(True,False),(False,True),(False,False)])
def test_reset_expiry_single_use_and_session_invalidation(client, registered, auth, expired, used):
    token = 'a' * 43
    db = db_session()
    db.add(AccountToken(digest=hashlib.sha256(token.encode()).hexdigest(), user_id=registered['user']['id'], purpose='reset', used=used,
        expires_at=datetime.now(timezone.utc)+timedelta(minutes=-1 if expired else 10)))
    db.commit()
    r = client.post('/auth/reset-password', json={'token': token, 'password': 'Passw0rdNew'})
    if expired or used:
        assert r.status_code == 400
    else:
        assert r.status_code == 200
        assert client.get('/auth/me', headers=auth).status_code == 401
        assert client.post('/auth/reset-password', json={'token': token, 'password': 'Passw0rdNew'}).status_code == 400


def test_invalid_malformed_reset(client):
    assert client.post('/auth/reset-password', json={'token':'bad', 'password':'Passw0rdNew'}).status_code == 422
    assert client.post('/auth/reset-password', json={'token':'b'*43, 'password':'Passw0rdNew'}).status_code == 400


def test_verification_single_use(client, registered):
    token='v'*43
    db=db_session()
    db.add(AccountToken(digest=hashlib.sha256(token.encode()).hexdigest(), user_id=registered['user']['id'], purpose='verify', used=False,
        expires_at=datetime.now(timezone.utc)+timedelta(minutes=10)))
    db.commit()
    assert client.post('/auth/verify-email',json={'token':token}).status_code == 200
    assert client.post('/auth/verify-email',json={'token':token}).status_code == 400
    assert db.get(AccountSecurity,registered['user']['id']).email_verified


def test_email_requires_verified_account(client, auth):
    assert client.post('/roadmap/email', headers=auth, json={'request_id':'synthetic-request-1234'}).status_code == 403


def test_roadmap_email_mock_and_idempotency(client, auth, registered, monkeypatch):
    from tests.test_api_modules import set_role, answer, DEMO
    set_role(client, auth)
    answer(client, auth, DEMO)
    db = db_session()
    db.get(AccountSecurity,registered['user']['id']).email_verified = True
    db.commit()
    calls=[]
    def send(to, subject, content, key):
        calls.append((subject,content,key))
        return 'synthetic-provider-id'
    monkeypatch.setattr(email_service,'send_email',send)
    body={'request_id':'synthetic-roadmap-request-1234'}
    assert client.post('/roadmap/email',headers=auth,json=body).status_code == 200
    assert client.post('/roadmap/email',headers=auth,json=body).status_code == 200
    assert len(calls)==1 and '<ol>' in calls[0][1] and 'Machine Learning Engineer' in calls[0][1]


def test_docx_xml_entity_rejected():
    import io, zipfile
    from app.nlp.resume_parser import extract_text, UnsupportedResume
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        z.writestr('word/document.xml','<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///etc/passwd">]><x>&secret;</x>')
    with pytest.raises(UnsupportedResume,match='unsafe XML'):
        extract_text(data.getvalue(),'resume.docx')
