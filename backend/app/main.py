import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api import account
from app.api import auth, modules_core as mc, modules_progress as mp, profile
from app.core.config import get_settings

log = logging.getLogger("skillgraph")


def create_app() -> FastAPI:
    s = get_settings()
    s.assert_secure()
    app = FastAPI(title=s.APP_NAME, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=False,  # bearer tokens, no cookies
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Auth-Token", "X-Requested-With"],
    )

    routers = (account.router, auth.router, profile.router, mc.roles_router, mc.assessment_router, mc.resume_router, mc.skills_router, mc.gap_router,
               mp.roadmap_router, mp.learn_router, mp.jobs_router, mp.interview_router, mp.reco_router)
    for r in routers:
        app.include_router(r)
        app.include_router(r, prefix="/api", include_in_schema=False)  # /api/profile, /api/skill-gap, /api/resume/upload, ...
    app.include_router(mp.dash_router)  # already serves both /dashboard and /api/dashboard

    (Path(s.UPLOAD_DIR) / "photos").mkdir(parents=True, exist_ok=True)  # NOT mounted: files are served only via authenticated endpoints

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "demo_mode": s.DEMO_MODE, "phase": 13}

    @app.exception_handler(SQLAlchemyError)
    async def db_error(request: Request, exc: SQLAlchemyError):
        log.error("database error on %s (%s)", request.url.path, type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "The database is unavailable. Please try again shortly."})

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.error("unhandled error on %s (%s)", request.url.path, type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side."})

    return app


app = create_app()
