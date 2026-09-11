import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

import auth
from database import engine, get_db
from services.curriculum import seed_topics
import models  # noqa: F401 — ensures all models are registered on Base
from routers import export, lessons, progress, questions, topics

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("mathsai")
logger.setLevel(logging.INFO)
_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "mathsai.log"), maxBytes=1_000_000, backupCount=3
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
logger.addHandler(_handler)
logger.addHandler(logging.StreamHandler())


@asynccontextmanager
async def lifespan(app: FastAPI):
    inspector = inspect(engine)
    if "topics" not in inspector.get_table_names():
        logger.warning(
            "Database tables not found — run `alembic upgrade head` before starting the app."
        )
    else:
        db: Session = next(get_db())
        try:
            seed_topics(db)
        finally:
            db.close()
    yield


# Refuses to construct the app at all if this is a production deployment
# with authentication unconfigured. Raising here is deliberate: the failure
# mode it prevents (a public URL with open regenerate routes spending
# Anthropic credits) is silent, and a crash on boot is not.
auth.check_auth_config()

app = FastAPI(title="MathsAI", lifespan=lifespan)

# Never "*" (CLAUDE.md CORS and health checks). In the normal deployment path
# (single container serving both frontend and API) the frontend is served by
# this same app on the same origin, so browsers never send a cross-origin
# request here at all; this only matters for the local case of pointing a
# separately-run frontend dev server directly at the API without Vite's proxy.
_frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",")
    if origin.strip()
]

# Middleware order matters and is the reverse of the order added: the last
# one added is outermost and runs first. The required runtime order is
# CORS (so preflight is answered before anything can reject it) → Session
# (so `scope["session"]` is populated) → Auth (which reads that session).
app.add_middleware(auth.AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.session_secret(),
    session_cookie=auth.SESSION_COOKIE,
    max_age=auth.SESSION_MAX_AGE,
    same_site="lax",
    # Cookie is HTTPS-only in production; relaxed locally so plain-http
    # `uvicorn --reload` still works. Starlette always sets HttpOnly.
    https_only=auth.is_production(),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registered before the SPA catch-all below, which would otherwise swallow
# GET /login.
app.include_router(auth.router)
app.include_router(auth.page_router)

app.include_router(topics.router)
app.include_router(lessons.router)
app.include_router(questions.router)
app.include_router(progress.router)
app.include_router(export.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serves the production frontend build (Docker copies `frontend/dist` here as
# `backend/static/` — see Dockerfile) from the same origin as the API, so no
# CORS or separate web server is needed in deployment. Registered last and
# gated on the directory existing so local `uvicorn main:app --reload`
# without a frontend build (and the pytest suite) are unaffected — the Vite
# dev proxy handles the local frontend/backend split instead.
_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_FRONTEND_DIST):
    app.mount(
        "/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets"
    )

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
