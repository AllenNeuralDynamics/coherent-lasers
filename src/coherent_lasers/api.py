#!/usr/bin/env python3
import asyncio
import logging
from typing import Any
from collections.abc import Generator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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


# ----------------------------------------------------------------------------------------------------------------------
# Dependency: Get a GenesisMX device for a given serial.
# ----------------------------------------------------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------------------------------------------------------
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


def get_device_status(serial: str) -> StatusResponse:
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


def get_device_power(serial: str) -> PowerStatus:
    device = get_device(serial)
    power = device.power
    return PowerStatus(value=power.value, setpoint=power.setpoint)


@app.get("/api/device/{serial}/status", response_model=StatusResponse)
async def get_status(serial: str):
    """
    Retrieve a detailed status report from the device.
    """
    return await run_in_threadpool(get_device_status, serial)


@app.post("/api/device/{serial}/enable", response_model=StatusResponse)
async def enable_device(serial: str):
    """Enable the device."""
    device = get_device(serial)
    await run_in_threadpool(device.enable)
    # device.enable()
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


class wsManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Use a copy of the list so we can safely remove connections if needed.
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                self.disconnect(connection)


ws_managers: dict[str, wsManager] = {}


# @app.websocket("/ws/device/{serial}")
# async def device_ws(websocket: WebSocket, serial: str):
#     if serial not in ws_managers:
#         ws_managers[serial] = wsManager()
#     ws_manager = ws_managers[serial]

#     await ws_manager.connect(websocket)
#     counter = 0
#     try:
#         while True:
#             power = get_device_power(serial)
#             power_update = {
#                 "type": "power_update",
#                 "data": {
#                     "value": power.value,
#                     "setpoint": power.setpoint,
#                 },
#             }
#             await ws_manager.broadcast(power_update)

#             counter += 1
#             if counter % 10 == 0:
#                 status = await run_in_threadpool(get_device_status, serial)
#                 full_update = {
#                     "type": "full_status",
#                     "data": status.model_dump(),  # sends the complete status
#                 }
#                 await ws_manager.broadcast(full_update)
#             await asyncio.sleep(0.1)
#     except WebSocketDisconnect:
#         ws_manager.disconnect(websocket)
#     except Exception as e:
#         logger.error(f"Websocket error for device {serial}: {e}")
#     finally:
#         await websocket.close()


@app.websocket("/ws/device/{serial}")
async def device_ws(websocket: WebSocket, serial: str):
    if serial not in ws_managers:
        ws_managers[serial] = wsManager()
    ws_manager = ws_managers[serial]

    await ws_manager.connect(websocket)

    # Spawn the update loop as a background task.
    update_task = asyncio.create_task(websocket_update_loop(ws_manager, serial))

    try:
        # Optionally, wait here until the websocket disconnects.
        await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Websocket error for device {serial}: {e}")
    finally:
        update_task.cancel()  # Cancel the update loop if the websocket disconnects.
        await websocket.close()


async def websocket_update_loop(ws_manager: wsManager, serial: str):
    counter = 0
    try:
        while True:
            power = get_device_power(serial)
            power_update = {
                "type": "power_update",
                "data": {
                    "value": power.value,
                    "setpoint": power.setpoint,
                },
            }
            await ws_manager.broadcast(power_update)

            counter += 1
            if counter % 10 == 0:
                status = await run_in_threadpool(get_device_status, serial)
                full_update = {
                    "type": "full_status",
                    "data": status.model_dump(),  # sends the complete status
                }
                await ws_manager.broadcast(full_update)
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        # Task was cancelled when the websocket closed.
        pass


if __name__ == "__main__":
    try:
        uvicorn.run("coherent_lasers.api:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down.")
