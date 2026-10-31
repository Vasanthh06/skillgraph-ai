from datetime import date
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class ExperienceLevel(str, Enum):
    fresher = "fresher"
    internship = "internship"
    y0_1 = "0-1"
    y1_3 = "1-3"
    y3_5 = "3-5"
    y5_plus = "5+"


class EducationLevel(str, Enum):
    high_school = "high_school"
    diploma = "diploma"
    bachelors = "bachelors"
    masters = "masters"
    phd = "phd"
    other = "other"


def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _url(v: str | None) -> str | None:
    v = _clean(v)
    if v and not (v.startswith("https://") or v.startswith("http://")):
        raise ValueError("Must start with http:// or https://")
    return v


class ProfileUpdate(BaseModel):
    """All fields optional so the profile can be completed in steps."""

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=120)
    linkedin_url: str | None = Field(default=None, max_length=300)
    github_url: str | None = Field(default=None, max_length=300)
    portfolio_url: str | None = Field(default=None, max_length=300)
    degree: str | None = Field(default=None, max_length=120)
    university: str | None = Field(default=None, max_length=160)
    graduation_year: int | None = Field(default=None, ge=1950, le=date.today().year + 8)
    education_level: EducationLevel | None = None
    experience_level: ExperienceLevel | None = None
    target_role: str | None = Field(default=None, max_length=120)

    @field_validator("linkedin_url", "github_url", "portfolio_url")
    @classmethod
    def _urls(cls, v):
        return _url(v)

    @field_validator("phone", "location", "degree", "university", "target_role")
    @classmethod
    def _strings(cls, v):
        return _clean(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        if v and not all(c.isdigit() or c in "+-() " for c in v):
            raise ValueError("Phone may contain digits, spaces, + - ( ) only")
        return v


class ProfileOut(BaseModel):
    full_name: str
    email: EmailStr
    photo_url: str | None
    phone: str | None
    location: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    degree: str | None
    university: str | None
    graduation_year: int | None
    education_level: str | None
    experience_level: str | None
    target_role: str | None
    # Onboarding state, computed on the server so the client can't drift.
    profile_complete: bool
    missing_fields: list[str]
