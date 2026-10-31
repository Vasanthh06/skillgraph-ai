import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def _check_password(v: str) -> str:
    from app.core.config import get_settings
    if not get_settings().DEMO_MODE:
        if not 15 <= len(v) <= 128:
            raise ValueError("Use 15–128 characters; passphrases and spaces are welcome")
        if v.lower() in {"passwordpassword", "123456789012345", "thisisapassword"}:
            raise ValueError("Choose a less common password")
        return v
    if len(v.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes")
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("Password must contain at least one letter and one number")
    return v


def _normalise_email(v):
    # mode="before": strip/lower BEFORE EmailStr validates, so an address copy-pasted with
    # surrounding spaces or capitals ("  Preview@Example.COM ") is accepted instead of 422.
    return v.strip().lower() if isinstance(v, str) else v


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str
    adult_eligible: bool = False
    terms_accepted: bool = False
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Name is too short")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        return _normalise_email(v)

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return _check_password(v)

    @model_validator(mode="after")
    def _match(self):
        from app.core.config import get_settings
        if not get_settings().DEMO_MODE and not (self.adult_eligible and self.terms_accepted):
            raise ValueError("You must be at least 18 and accept the terms and privacy notice")
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        return _normalise_email(v)


class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserOut
