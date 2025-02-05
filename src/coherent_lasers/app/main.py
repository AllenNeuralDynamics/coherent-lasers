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
    "http://127.0.0.1:8000",
]


def kill_python_processes():
    import psutil
    import os

    my_pid = os.getpid()

    for proc in psutil.process_iter():
        try:
            # Get process name & pid from process object.
            processName = proc.name()
            processID = proc.pid

            if proc.pid == my_pid:
                print("I am not suicidal")
                continue

            if processName.startswith("python3"):  # adapt this line to your needs
                print(
                    f"I will kill {processName}[{processID}] : {''.join(proc.cmdline())})"
                )
                # proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            print(e)


genesis_mx_router = GenesisMXRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event for FastAPI app: Initializes lasers and starts background tasks."""
    await genesis_mx_router.start_broadcast_tasks()
    yield
    kill_python_processes()
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
