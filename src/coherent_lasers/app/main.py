from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from .api import GenesisMXRouter

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:4173",
]

genesis_mx_router = GenesisMXRouter(num_mock_lasers=3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event for FastAPI app: Initializes lasers and starts background tasks."""
    await genesis_mx_router.start_broadcast_tasks()
    yield
    # await genesis_mx_router.stop_broadcast_tasks()
    # await genesis_mx_router.ws_manager.shutdown()


app = FastAPI(lifespan=lifespan, redirect_slashes=True)
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genesis_mx_router.redirect_slashes = True

app.include_router(genesis_mx_router, prefix="/api")

# Serve spa
frontend_build_dir = Path(__file__).parent / "frontend" / "build"
app.mount("/", StaticFiles(directory=frontend_build_dir, html=True), name="app")


def run():
    try:
        uvicorn.run(app, log_level="info")
    except KeyboardInterrupt:
        print("Shutdown requested. Exiting...")


if __name__ == "__main__":
    run()
