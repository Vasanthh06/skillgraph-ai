"""Create the spec §50 demo user. Requires DEMO_MODE=true:  python scripts/seed_demo.py

The account is flagged is_demo_account, so it cannot authenticate when the app runs with DEMO_MODE=false.

Rahul Kumar, target Machine Learning Engineer, with the assessment from the spec. Everything the dashboard then
shows is computed by the real engine from these self-assessment answers. Nothing is hard-coded.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import Base, UserSkillAssessment  # noqa: E402
from app.repositories import users as repo  # noqa: E402
from app.schemas.profile import ProfileUpdate  # noqa: E402
from app.services import analysis, profile_service  # noqa: E402
from app.services.seed import ensure_seeded, skill_maps  # noqa: E402

DEMO_EMAIL, DEMO_PASSWORD = "rahul@demo.skillgraph.ai", "DemoPass123"
ASSESSMENT = {  # spec §50
    "python": "intermediate", "sql": "intermediate", "pandas": "beginner", "numpy": "beginner", "git": "intermediate",
    "statistics": "beginner", "machine-learning": "beginner", "deep-learning": "never_used", "pytorch": "never_used",
    "docker": "never_used", "aws": "never_used",
}

if __name__ == "__main__":
    if not get_settings().DEMO_MODE:
        raise SystemExit("Refusing to seed demo data: DEMO_MODE is false.")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_seeded(db)
        if repo.get_by_email(db, DEMO_EMAIL):
            raise SystemExit("Demo user already exists.")
        user = repo.create_user_with_profile(db, full_name="Rahul Kumar", email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD))
        user.is_demo_account = True   # can only log in while DEMO_MODE=true
        db.commit()
        profile_service.update(db, user, ProfileUpdate(location="Bengaluru", education_level="bachelors", experience_level="fresher",
                                                       target_role="Machine Learning Engineer", degree="B.Tech", graduation_year=2025))
        to_id, _ = skill_maps(db)
        for slug, level in ASSESSMENT.items():
            db.add(UserSkillAssessment(user_id=user.id, skill_id=to_id[slug], self_level=level))
        db.commit()
        a = analysis.refresh(db, user)
        print(f"Created {DEMO_EMAIL} / {DEMO_PASSWORD}. Computed readiness: {a.readiness['overall']}%")
