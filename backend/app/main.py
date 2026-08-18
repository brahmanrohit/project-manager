from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app import models  # noqa: F401
from app.routers import auth, dashboard, projects, tasks, users

app = FastAPI(title=settings.app_name, debug=settings.debug)

# Only the real frontend may call the API with credentials.
# "*" plus allow_credentials is rejected by browsers anyway, so it never worked.
allowed_origins = [settings.frontend_url]
if not settings.is_production:
    allowed_origins += ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(allowed_origins)),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Tables are created by Alembic only. Run `alembic upgrade head` before start.
# The old create_all() on startup let the app boot on a stale schema, and it
# also made Alembic think it had built a database it never touched.


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    # Same check under /api, because the deploy config points here.
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(users.router, prefix="/api")
