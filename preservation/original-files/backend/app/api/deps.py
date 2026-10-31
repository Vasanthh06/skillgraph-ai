import logging

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models import User
from app.repositories import users as repo

log = logging.getLogger("skillgraph.auth")

bearer = HTTPBearer(auto_error=False)
_401 = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})


def get_token_payload(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_auth_token: str | None = Header(default=None, alias="X-Auth-Token"),
    db: Session = Depends(get_db),
) -> dict:
    # The web app sends the token twice: `Authorization: Bearer ...` (standard) AND
    # `X-Auth-Token: ...` (fallback). Verified failure in a proxied preview: login returned
    # 200 but the immediately following /dashboard and /profile got 401 (and the UI bounced
    # back to /login), i.e. the Authorization header was missing/unusable on those requests
    # somewhere between the browser and here, while the same flow worked locally. Accepting
    # the first credential that verifies makes the session work either way. Reasons are
    # logged (never token values) so a failing 401 says WHY instead of only "Not authenticated".
    candidates: list[tuple[str, str]] = []
    if creds is not None and creds.credentials:
        candidates.append(("authorization", creds.credentials))
    if x_auth_token:
        token = x_auth_token[7:].strip() if x_auth_token.lower().startswith("bearer ") else x_auth_token.strip()
        if token:
            candidates.append(("x-auth-token", token))

    reasons: list[str] = []
    for source, token in candidates:
        try:
            payload = decode_token(token)
        except jwt.PyJWTError as e:  # expired / bad signature / malformed -- record which, not the token
            reasons.append(f"{source}: {type(e).__name__} (len={len(token)})")
            continue
        if repo.is_revoked(db, payload.get("jti", "")):
            reasons.append(f"{source}: revoked")
            continue
        if source != "authorization":
            # WARNING (not INFO): uvicorn doesn't configure this logger, so INFO would be
            # invisible in server logs -- and this anomalous-but-recovered case is exactly
            # what needs to be visible when diagnosing "login doesn't navigate" reports.
            log.warning("auth: %s %s authenticated via %s fallback (Authorization unusable: %s)",
                        request.method, request.url.path, source, "; ".join(reasons) or "missing")
        return payload

    log.warning("auth: 401 for %s %s -- %s [authorization present=%s, x-auth-token present=%s]",
                request.method, request.url.path, "; ".join(reasons) or "no credentials",
                creds is not None, bool(x_auth_token))
    raise _401


def get_current_user(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> User:
    # The user identity comes ONLY from the verified token. No endpoint accepts a user id from the client.
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        log.warning("auth: 401 -- token payload has no subject")
        raise _401
    user = repo.get_by_id(db, sub)
    if user is None or not user.is_active:
        log.warning("auth: 401 -- token subject is not an active user")
        raise _401
    if user.is_demo_account and not get_settings().DEMO_MODE:
        log.warning("auth: 401 -- demo account outside DEMO_MODE")
        raise _401  # demo accounts are inert outside DEMO_MODE
    return user
