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

    # 1. Add security_headers FIRST (so CORS runs outermost)
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    # 2. Add CORS LAST (so it's the outermost layer and handles preflight first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://skillgraph-frontend-ymhr.onrender.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Auth-Token", "X-Requested-With"],
    )

    routers = (account.router, auth.router, profile.router, mc.roles_router, mc.assessment_router, mc.resume_router, mc.skills_router, mc.gap_router,
               mp.roadmap_router, mp.learn_router, mp.jobs_router, mp.interview_router, mp.reco_router)
    for r in routers:
        app.include_router(r)
        app.include_router(r, prefix="/api", include_in_schema=False)
    app.include_router(mp.dash_router)

    (Path(s.UPLOAD_DIR) / "photos").mkdir(parents=True, exist_ok=True)

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