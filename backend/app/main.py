"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routers import libraries, media, rename, scrape, settings as settings_router, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="MediaManager API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(libraries.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")
app.include_router(rename.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")

# Serve the mounted media library (posters / backdrops live next to media files)
# so the frontend can <img src="/media/...">.
settings.media_root.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(settings.media_root)), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok", "tmdb_configured": bool(settings.tmdb_api_key)}


@app.get("/")
def root():
    return {"name": "MediaManager API", "docs": "/docs"}
