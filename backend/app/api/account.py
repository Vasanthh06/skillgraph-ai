"""Additive lifecycle API. Tokens never appear in responses or logs."""
import hashlib
import html
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password
from app.models import User
from app.models.account import AccountSecurity, AccountToken, EmailDelivery
from app.schemas.auth import _check_password
from app.services import email_service
from app.utils.rate_limit import auth_rate_limit

router = APIRouter(tags=["account lifecycle"])
GENERIC = {"message": "If the account is eligible, an email will arrive. Check your inbox shortly."}


def security(db, user):
    row = db.get(AccountSecurity, user.id)
    if row is None:
        row = AccountSecurity(user_id=user.id)
        db.add(row)
        db.flush()
    return row


def issue(db, user, purpose):
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = AccountToken(digest=digest, user_id=user.id, purpose=purpose,
                       expires_at=datetime.now(timezone.utc) + timedelta(minutes=20))
    db.add(row)
    db.commit()
    s = get_settings()
    if not s.APP_URL.startswith("https://") and s.COOKIE_SECURE:
        raise HTTPException(503, "Production APP_URL must use HTTPS")
    url = f"{s.APP_URL.rstrip('/')}/account/{purpose}#token={quote(token)}"
    try:
        email_service.send_email(user.email, "SkillGraph account " + purpose,
            f'<p>This link expires in 20 minutes and can be used once.</p><p><a href="{html.escape(url, quote=True)}">Continue securely</a></p>', digest)
    except email_service.EmailUnavailable:
        # Generic response still prevents account enumeration. Failed tokens cannot be used.
        row.used = True
        db.commit()


def consume(db, token, purpose):
    digest = hashlib.sha256(token.encode()).hexdigest()
    # Atomic conditional UPDATE prevents concurrent token replay across workers.
    result = db.execute(update(AccountToken).where(AccountToken.digest == digest,
        AccountToken.purpose == purpose, AccountToken.used.is_(False),
        AccountToken.expires_at > datetime.now(timezone.utc)).values(used=True))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(400, "Invalid, expired, or already used link")
    return db.get(AccountToken, digest)


class EmailIn(BaseModel):
    email: EmailStr


class TokenIn(BaseModel):
    token: str = Field(min_length=40, max_length=100)


class ResetIn(TokenIn):
    password: str = Field(min_length=1, max_length=128)


@router.post("/auth/forgot-password", dependencies=[Depends(auth_rate_limit)])
def forgot(body: EmailIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.is_active.is_(True)))
    if user:
        issue(db, user, "reset")
    return GENERIC


@router.post("/auth/reset-password", dependencies=[Depends(auth_rate_limit)])
def reset(body: ResetIn, db: Session = Depends(get_db)):
    try:
        _check_password(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    row = consume(db, body.token, "reset")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        db.rollback()
        raise HTTPException(400, "Invalid link")
    user.hashed_password = hash_password(body.password)
    security(db, user).valid_after = int(time.time()) + 1
    db.execute(update(AccountToken).where(AccountToken.user_id.in_([user.id]), AccountToken.purpose == "reset").values(used=True))
    db.commit()
    return {"message": "Password updated. Existing sessions have been invalidated; sign in again."}


@router.post("/auth/request-verification", dependencies=[Depends(auth_rate_limit)])
def request_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not security(db, user).email_verified:
        issue(db, user, "verify")
    return GENERIC


@router.post("/auth/verify-email", dependencies=[Depends(auth_rate_limit)])
def verify(body: TokenIn, db: Session = Depends(get_db)):
    row = consume(db, body.token, "verify")
    security(db, db.get(User, row.user_id)).email_verified = True
    db.commit()
    return {"message": "Email verified."}


@router.get("/account/status")
def account_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = security(db, user)
    db.commit()
    return {"email_verified": row.email_verified, "is_admin": row.is_admin,
            "consent_version": row.consent_version, "email_configured": bool(get_settings().RESEND_API_KEY and get_settings().EMAIL_FROM)}


class DeliveryIn(BaseModel):
    request_id: str = Field(pattern=r"^[a-zA-Z0-9-]{16,64}$")


@router.post("/roadmap/email", dependencies=[Depends(auth_rate_limit)])
def roadmap_email(body: DeliveryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not security(db, user).email_verified:
        raise HTTPException(403, "Verify your email before requesting roadmap delivery")
    from app.services import analysis, views
    roadmap = views.roadmap_view(analysis.analyze_user(db, user))
    if roadmap.get("needs") or not roadmap.get("nodes"):
        raise HTTPException(409, "Complete your profile and assessment first")
    key = hashlib.sha256(f"{user.id}:{body.request_id}".encode()).hexdigest()
    delivery = db.get(EmailDelivery, key)
    if delivery and delivery.status == "sent":
        return {"status": "sent"}
    if delivery and delivery.status == "pending":
        raise HTTPException(409, "Delivery in progress; do not create a new request")
    if delivery is None:
        delivery = EmailDelivery(id=key, user_id=user.id, kind="roadmap", status="pending")
        db.add(delivery)
    else:
        delivery.status = "pending"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Delivery already requested")
    nodes = "".join(f'<li>{html.escape(str(n["name"]))} — {html.escape(str(n["status"]))}</li>' for n in roadmap["nodes"])
    content = f'<h1>Your learning roadmap</h1><p>Goal: {html.escape(str(roadmap.get("role", "")))}</p><ol>{nodes}</ol><p><a href="{html.escape(get_settings().APP_URL.rstrip("/") + "/roadmap", quote=True)}">View progress securely</a></p>'
    try:
        delivery.provider_id = email_service.send_email(user.email, "Your SkillGraph roadmap", content, key)
        delivery.status = "sent"
        db.commit()
    except email_service.EmailUnavailable:
        delivery.status = "failed"
        db.commit()
        raise HTTPException(503, "Email is not configured or provider unavailable. Retry the same request later.")
    return {"status": "sent"}


def admin(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not security(db, user).is_admin:
        raise HTTPException(403, "Administrator permission required")
    return user


@router.get("/admin/users")
def users(offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
          q: str = Query("", max_length=80), actor: User = Depends(admin), db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    if q:
        stmt = stmt.where(User.full_name.ilike("%" + q.replace("%", "").replace("_", "") + "%"))
    rows = db.scalars(stmt).all()
    return {"offset": offset, "limit": limit, "users": [{"id": u.id, "full_name": u.full_name,
        "created_at": u.created_at, "is_active": u.is_active,
        "email_verified": bool(db.get(AccountSecurity, u.id) and db.get(AccountSecurity, u.id).email_verified),
        "target_role": u.profile.target_role if u.profile else None} for u in rows]}
