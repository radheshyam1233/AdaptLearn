# app/main.py
# Entry point: creates the app and plugs everything in.
# Run locally with:  uvicorn app.main:app --reload

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import models  # noqa: F401  (loads the table classes so create_all sees them)
from .database import Base, engine
from .routers import analytics, attempts, auth, live, questions
from .services.cache import redis_ok


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: create any missing tables.
    # (In a bigger project you'd use Alembic migrations instead.)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AdaptLearn API", version="1.0.0", lifespan=lifespan)

# CORS: the browser blocks a page on one origin (localhost:5173) from calling an
# API on another (localhost:8000) unless the API explicitly allows it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(questions.router)
app.include_router(attempts.router)
app.include_router(analytics.router)
app.include_router(live.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "redis": redis_ok()}
