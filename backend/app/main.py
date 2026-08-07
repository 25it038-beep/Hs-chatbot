import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import auth, chats, models, files, nvidia_api
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.nvidia.warmup import start_warmup, stop_warmup

os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs("./data", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_warmup()
    yield
    await stop_warmup()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

cors_origins = settings.cors_origin_list

if "*" in cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(models.router)
app.include_router(files.router)
app.include_router(nvidia_api.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.app_version, "env": settings.app_env}


@app.get("/")
async def root():
    return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs"}
