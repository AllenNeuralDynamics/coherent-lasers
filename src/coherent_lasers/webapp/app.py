from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import GenesisMXRouter

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:4173",
]

genesis_mx_router = GenesisMXRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event for FastAPI app: Initializes lasers and starts background tasks."""
    await genesis_mx_router.start_broadcast_tasks()
    yield
    await genesis_mx_router.stop_broadcast_tasks()
    await genesis_mx_router.ws_manager.shutdown()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# get the frontend build directory as pathlib.Path(__file__).parent.parent / "frontend" / "build"

frontend_build_dir = Path(__file__).parent / "frontend" / "build"

app.mount("/", StaticFiles(directory=frontend_build_dir, html=True), name="static")

app.include_router(GenesisMXRouter(), prefix="/api/genesis-mx")


def run():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
