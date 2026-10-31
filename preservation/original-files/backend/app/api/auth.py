from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_token_payload
from app.core.database import get_db
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services import auth_service
from app.utils.rate_limit import auth_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201, dependencies=[Depends(auth_rate_limit)])
def register(data: RegisterIn, db: Session = Depends(get_db)):
    try:
        return auth_service.register(db, data)
    except auth_service.EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")


@router.post("/login", response_model=TokenOut, dependencies=[Depends(auth_rate_limit)])
def login(data: LoginIn, db: Session = Depends(get_db)):
    try:
        return auth_service.login(db, data)
    except auth_service.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    auth_service.logout(db, payload["jti"], payload["exp"])
