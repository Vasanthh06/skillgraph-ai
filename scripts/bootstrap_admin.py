"""Explicit one-time operator command. Never resets an existing account's password."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.schemas.auth import _check_password
from app.repositories.users import get_by_email, create_user_with_profile
from app.models.account import AccountSecurity
s = get_settings()
s.assert_secure()
if not s.ADMIN_BOOTSTRAP_ENABLED or not s.ADMIN_EMAIL or not s.ADMIN_PASSWORD:
    raise SystemExit('Explicitly enable bootstrap and supply server-side ADMIN_EMAIL and ADMIN_PASSWORD')
_check_password(s.ADMIN_PASSWORD)
with SessionLocal() as db:
    if get_by_email(db, s.ADMIN_EMAIL):
        raise SystemExit('Account already exists: refusing password reset or privilege promotion')
    u = create_user_with_profile(db, full_name='Administrator', email=s.ADMIN_EMAIL, hashed_password=hash_password(s.ADMIN_PASSWORD))
    db.add(AccountSecurity(user_id=u.id, is_admin=True))
    db.commit()
print('Administrator provisioned. Disable bootstrap and remove ADMIN_PASSWORD now. Verify email normally.')
