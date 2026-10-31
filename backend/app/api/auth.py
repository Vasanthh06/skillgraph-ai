from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from app.core.config import get_settings
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_token_payload
from app.core.database import get_db
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services import auth_service
from app.utils.rate_limit import auth_rate_limit

def session_response(result, response, request):
    s = get_settings()
    if request.headers.get("x-requested-with") != "SkillGraph":
        return result
    response.set_cookie("sg_session", result.access_token, httponly=True, secure=s.COOKIE_SECURE,
                        samesite="lax", max_age=s.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/")
    response.headers["Cache-Control"] = "no-store"
    return result

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201, dependencies=[Depends(auth_rate_limit)])
def register(data: RegisterIn, response: Response, request: Request, db: Session = Depends(get_db)):
    try:
        return session_response(auth_service.register(db, data), response, request)
    except auth_service.EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")


@router.post("/login", response_model=TokenOut, dependencies=[Depends(auth_rate_limit)])
def login(data: LoginIn, response: Response, request: Request, db: Session = Depends(get_db)):
    try:
        return session_response(auth_service.login(db, data), response, request)
    except auth_service.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(response: Response, payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    auth_service.logout(db, payload["jti"], payload["exp"])
    response.delete_cookie("sg_session", path="/")
