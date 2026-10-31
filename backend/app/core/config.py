from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "change-me-in-env"

# "./.env" alone depended on the CURRENT WORKING DIRECTORY: following the README
# (`cp .env.example .env` at the repo root, then uvicorn from backend/) meant the
# backend never saw that root .env, so it refused to start without a real SECRET_KEY —
# and the frontend login then only said "Can't reach the server". Look in all three
# obvious places (real OS environment variables still take precedence over all of them).
_BACKEND_DIR = Path(__file__).resolve().parents[2]  # app/core/config.py -> backend/
_ENV_FILES = (".env", str(_BACKEND_DIR / ".env"), str(_BACKEND_DIR.parent / ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")

    APP_URL: str = "http://localhost:5173"
    COOKIE_SECURE: bool = False
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = ""
    ADMIN_BOOTSTRAP_ENABLED: bool = False
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    APP_NAME: str = "SkillGraph AI"
    # Normal operation is DEMO_MODE=false. Demo accounts and sample users only work when this is true.
    DEMO_MODE: bool = False
    DATABASE_URL: str = "postgresql+psycopg2://skillgraph:skillgraph@localhost:5432/skillgraph"
    SECRET_KEY: str = INSECURE_DEFAULT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173"
    UPLOAD_DIR: str = "uploads"
    MAX_PHOTO_BYTES: int = 2 * 1024 * 1024
    YOUTUBE_API_KEY: str = ""
    MAX_RESUME_BYTES: int = 5 * 1024 * 1024
    RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT: int = 10  # requests per window per client
    AUTH_RATE_WINDOW_SECONDS: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def assert_secure(self) -> None:
        """Refuse to start outside demo mode with a placeholder/weak secret."""
        if not self.DEMO_MODE and (self.SECRET_KEY == INSECURE_DEFAULT_SECRET or len(self.SECRET_KEY) < 32):
            raise RuntimeError("SECRET_KEY must be a random value of 32+ characters when DEMO_MODE=false")


@lru_cache
def get_settings() -> Settings:
    return Settings()
