from sqlalchemy.orm import Session

from app.models import User
from app.engine.catalog import get_catalog
from app.services import analysis
from app.schemas.profile import ProfileOut, ProfileUpdate

# Fields that must be filled before onboarding can move on to target-role assessment.
REQUIRED_FOR_COMPLETE = {
    "location": "Location",
    "education_level": "Education level",
    "experience_level": "Experience",
    "target_role": "Target role",
}


def to_out(user: User) -> ProfileOut:
    p = user.profile
    missing = [label for field, label in REQUIRED_FOR_COMPLETE.items() if not getattr(p, field)]
    return ProfileOut(
        full_name=user.full_name,
        email=user.email,
        photo_url="/profile/photo" if p.photo_url else None,
        phone=p.phone,
        location=p.location,
        linkedin_url=p.linkedin_url,
        github_url=p.github_url,
        portfolio_url=p.portfolio_url,
        degree=p.degree,
        university=p.university,
        graduation_year=p.graduation_year,
        education_level=p.education_level,
        experience_level=p.experience_level,
        target_role=p.target_role,
        profile_complete=not missing,
        missing_fields=missing,
    )


def update(db: Session, user: User, data: ProfileUpdate) -> ProfileOut:
    changes = data.model_dump(exclude_unset=True)
    if "full_name" in changes:
        name = changes.pop("full_name")
        if name:
            user.full_name = " ".join(name.split())
    role_changed = "target_role" in changes and changes["target_role"] != user.profile.target_role
    for field, value in changes.items():
        # enums -> plain strings for storage
        setattr(user.profile, field, getattr(value, "value", value))
    if role_changed:
        spec = analysis.resolve_role(get_catalog(), user.profile.target_role)
        user.profile.target_role_id = analysis.ensure_role_row(db, spec).id if spec else None
        analysis.log_activity(db, user.id, "role_changed", meta={"role": user.profile.target_role})
    db.commit()
    db.refresh(user)
    if role_changed:
        analysis.refresh(db, user)  # spec §58: every module recalculates; existing skills are kept
    return to_out(user)
