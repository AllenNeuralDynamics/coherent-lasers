#!/usr/bin/env python3
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from collections.abc import Generator

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager, run_in_threadpool
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# Import your GenesisMX class and HOPS manager factory.
from coherent_lasers.genesis import GenesisMX
from coherent_lasers.hops.cohrhops import CohrHOPSManager, get_cohrhops_manager

logger = logging.getLogger("laser_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DEVICES: dict[str, GenesisMX] = {}


# Use a safe initializer to mark threads as daemon.
def safe_set_daemon():
    try:
        threading.current_thread().daemon = True
    except Exception as e:
        logger.warning(f"Failed to set thread as daemon: {e}")


# Create a thread pool for running blocking device calls.
# executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="daemon", initializer=safe_set_daemon)


# async def run_blocking(func, *args, **kwargs):
#     loop = asyncio.get_running_loop()
#     return await loop.run_in_executor(executor, func, *args, **kwargs)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Lifespan event for FastAPI app: Initializes lasers and starts background tasks."""
#     run_discovery()
#     yield
#     # executor.shutdown(wait=False)
#     get_cohrhops_manager().close()
#     # logger.info("Executor shutdown, cleaning up.")


def run_discovery():
    DEVICES.clear()
    for serial in get_cohrhops_manager().discover():
        DEVICES[serial] = GenesisMX(serial)
    logger.info(f"Discovered devices: {list(DEVICES.keys())}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run blocking discovery in a threadpool
    await run_in_threadpool(run_discovery)
    yield
    await run_in_threadpool(get_cohrhops_manager().close)


app = FastAPI(title="Laser Control API", version="0.1", lifespan=lifespan)
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------------------------------------------------------
# Pydantic models for request/response data.
# ----------------------------------------------------------------------------------------------------------------------
class DeviceInfo(BaseModel):
    serial: str
    wavelength: int
    head_type: str
    head_hours: str | None = None
    head_board_revision: str | None = None


class PowerStatus(BaseModel):
    value: float | None
    setpoint: float | None


class SetPowerRequest(BaseModel):
    power: float


class StatusResponse(BaseModel):
    remote_control: bool | None
    key_switch: bool | None
    interlock: bool | None
    software_switch: bool | None
    power: PowerStatus
    temperature: float | None
    current: float | None
    mode: int | None
    alarms: list[str] | None


# ----------------------------------------------------------------------------------------------------------------------
# Dependency: Provide a HOPS manager instance.
# ----------------------------------------------------------------------------------------------------------------------
def get_manager() -> Generator[CohrHOPSManager, Any, None]:
    manager: CohrHOPSManager = get_cohrhops_manager()
    try:
        yield manager
    finally:
        pass


# ---------------------------
# Dependency: Get a GenesisMX device for a given serial.
# ---------------------------
def get_device(serial: str) -> GenesisMX:
    try:
        if serial not in DEVICES:
            serials = get_cohrhops_manager().discover()
            if serial not in serials:
                raise HTTPException(status_code=404, detail=f"Device with serial {serial} not found.")
            DEVICES[serial] = GenesisMX(serial)
        return DEVICES[serial]
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Device with serial {serial} not found: {e}")


# ---------------------------
# API Endpoints
# ---------------------------
@app.get("/api/devices", response_model=list[str])
async def list_devices():
    """
    Discover and list all available device serial numbers.
    """
    if not DEVICES:
        run_discovery()
    serials = list(DEVICES.keys())
    if not serials:
        raise HTTPException(status_code=404, detail="No devices discovered.")
    return serials


@app.get("/api/device/{serial}/status", response_model=StatusResponse)
async def get_status(serial: str):
    """
    Retrieve a detailed status report from the device.
    """
    device = get_device(serial)
    power = device.power
    mode = device.mode
    return StatusResponse(
        remote_control=device.remote_control,
        key_switch=device.key_switch,
        interlock=device.interlock,
        software_switch=device.software_switch,
        power=PowerStatus(value=power.value, setpoint=power.setpoint),
        temperature=device.temperature,
        current=device.current,
        mode=mode.value if mode else None,
        alarms=device.alarms,
    )


@app.post("/api/device/{serial}/enable", response_model=StatusResponse)
async def enable_device(serial: str):
    """Enable the device."""
    device = get_device(serial)
    device.enable()
    return await get_status(serial)


@app.post("/api/device/{serial}/disable", response_model=StatusResponse)
async def disable_device(serial: str):
    """Disable the device."""
    device = get_device(serial)
    device.disable()
    return await get_status(serial)


@app.post("/api/device/{serial}/power", response_model=StatusResponse)
async def set_power(serial: str, request: SetPowerRequest):
    """Set the power of the device."""
    device = get_device(serial)
    device.power = request.power
    return await get_status(serial)


# @app.get("/api/device/{serial}/status", response_model=StatusResponse)
# async def get_status(serial: str):
#     """
#     Retrieve a detailed status report from the device.
#     """
#     device = get_device(serial)
#     remote_control = await run_blocking(lambda: device.remote_control)
#     key_switch = await run_blocking(lambda: device.key_switch)
#     interlock = await run_blocking(lambda: device.interlock)
#     software_switch = await run_blocking(lambda: device.software_switch)
#     power = await run_blocking(lambda: device.power)
#     temperature = await run_blocking(lambda: device.temperature)
#     current = await run_blocking(lambda: device.current)
#     mode = await run_blocking(lambda: device.mode)
#     alarms = await run_blocking(lambda: device.alarms)
#     return StatusResponse(
#         remote_control=remote_control,
#         key_switch=key_switch,
#         interlock=interlock,
#         software_switch=software_switch,
#         power=PowerStatus(value=power.value, setpoint=power.setpoint),
#         temperature=temperature,
#         current=current,
#         mode=mode.value if mode else None,
#         alarms=alarms,
#     )

# @app.post("/api/device/{serial}/enable", response_model=StatusResponse)
# async def enable_device(serial: str):
#     """Enable the device."""
#     device = get_device(serial)
#     await run_blocking(lambda: device.enable())
#     return await get_status(serial)


# @app.post("/api/device/{serial}/disable", response_model=StatusResponse)
# async def disable_device(serial: str):
#     """Disable the device."""
#     device = get_device(serial)
#     await run_blocking(lambda: device.disable())
#     return await get_status(serial)


# @app.post("/api/device/{serial}/power", response_model=StatusResponse)
# async def set_power(serial: str, request: SetPowerRequest):
#     """Set the power of the device."""

#     def set_power():
#         get_device(serial).power = request.power

#     await run_blocking(set_power)
#     return await get_status(serial)


# @app.on_event("shutdown")
# async def shutdown_event():
#     executor.shutdown(wait=False)
#     get_cohrhops_manager().close()
#     logger.info("Executor shutdown, cleaning up.")


if __name__ == "__main__":
    try:
        uvicorn.run("coherent_lasers.api:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down.")
