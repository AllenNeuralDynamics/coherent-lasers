#!/usr/bin/env python3
import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import asynccontextmanager, run_in_threadpool
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import your GenesisMX class and HOPS manager factory.
from coherent_lasers.genesis_mx import GenesisMX
from coherent_lasers.genesis_mx.hops import get_cohrhops_manager
from coherent_lasers.genesis_mx.mock import GenesisMXMock

logger = logging.getLogger("laser_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# -----------------------------------------------------------------------------
# WebSocket manager – maintains a list of active connections.
# -----------------------------------------------------------------------------
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
        # Optionally, you might want to force-close the websocket:
        # await websocket.close()

    async def broadcast(self, message: dict):
        # Iterate over a copy to safely remove closed connections.
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                self.disconnect(connection)


# -----------------------------------------------------------------------------
# Data structure for a device record.
#
# We add an optional 'publisher_task' attribute so that each device has
# only one background update loop that sends updates to all connected clients.
# -----------------------------------------------------------------------------
@dataclass
class DeviceRecord:
    instance: GenesisMX | GenesisMXMock
    socket: wsManager
    publisher_task: asyncio.Task | None = field(default=None)


# Global dictionary holding the discovered devices.
DEVICES: dict[str, DeviceRecord] = {}


def generate_mock_devices(num: int = 3) -> dict[str, DeviceRecord]:
    """Generate a dictionary of mock devices for testing."""
    colors = ["RED", "GREEN", "BLUE"]
    serials = [f"{colors[i % len(colors)]}-GENESIS-MX-MOCK-{i}" for i in range(num)]
    return {serial: DeviceRecord(GenesisMXMock(serial), wsManager()) for serial in serials}


def run_discovery(mock: bool = False):
    DEVICES.clear()
    try:
        for serial in get_cohrhops_manager().discover():
            DEVICES[serial] = DeviceRecord(GenesisMX(serial), wsManager())
        logger.info(f"Discovered devices: {list(DEVICES.keys())}")
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        if mock:
            logger.info("Using mock devices for testing.")
            DEVICES.update(generate_mock_devices())


# -----------------------------------------------------------------------------
# Lifespan: startup runs discovery; shutdown cancels any running publisher tasks
# and closes device resources.
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: run blocking discovery in a threadpool.
    await run_in_threadpool(run_discovery)
    yield
    # Shutdown: cancel any background publisher tasks and close devices.
    for record in DEVICES.values():
        if record.publisher_task is not None:
            record.publisher_task.cancel()
            try:
                await record.publisher_task
            except asyncio.CancelledError:
                logger.info("Publisher task cancelled.")
        # If GenesisMX has a close method, ensure it is run in the threadpool.
        if hasattr(record.instance, "close"):
            await run_in_threadpool(record.instance.close)
    # Finally, close the HOPS manager.
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


# -----------------------------------------------------------------------------
# Pydantic models for request/response data.
# -----------------------------------------------------------------------------
class DeviceInfo(BaseModel):
    serial: str
    wavelength: int
    head_type: str | None = None
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


# -----------------------------------------------------------------------------
# Dependency: Get a GenesisMX device for a given serial.
# -----------------------------------------------------------------------------
def get_device(serial: str) -> GenesisMX | GenesisMXMock:
    try:
        if serial not in DEVICES:
            # (If the device was not discovered at startup, try to discover it now.)
            serials = get_cohrhops_manager().discover()
            if serial not in serials:
                raise HTTPException(status_code=404, detail=f"Device with serial {serial} not found.")
            DEVICES[serial] = DeviceRecord(GenesisMX(serial), wsManager())
        return DEVICES[serial].instance
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Device with serial {serial} not found: {e}")


# -----------------------------------------------------------------------------
# Helper functions to get device status/power.
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/discover")
async def discover_devices(mock: bool = False):
    """Discover devices and return their serial numbers."""
    run_discovery(mock)
    return list(DEVICES.keys())


@app.get("/api/devices", response_model=list[str])
async def list_devices(mock: bool = False):
    """Discover and list all available device serial numbers."""
    if not DEVICES:
        run_discovery(mock)
    serials = list(DEVICES.keys())
    if not serials:
        raise HTTPException(status_code=404, detail="No devices discovered.")
    return serials


@app.get("/api/device/{serial}/status", response_model=StatusResponse)
async def get_status(serial: str):
    """Retrieve a detailed status report from the device."""

    def get_device_status_blocking():
        return get_device_status(serial)

    return await run_in_threadpool(get_device_status_blocking)


@app.get("/api/device/{serial}/info", response_model=DeviceInfo)
async def get_info(serial: str):
    """Retrieve device info."""
    device = get_device(serial)
    return DeviceInfo(
        serial=device.serial,
        wavelength=device.info.wavelength,
        head_type=device.info.head_type,
        head_hours=device.info.head_hours,
        head_board_revision=device.info.head_board_revision,
    )


@app.post("/api/device/{serial}/enable", response_model=StatusResponse)
async def enable_device(serial: str):
    """Enable the device."""
    device = get_device(serial)
    await run_in_threadpool(device.enable)
    return await get_status(serial)


@app.post("/api/device/{serial}/disable", response_model=StatusResponse)
async def disable_device(serial: str):
    """Disable the device."""
    device = get_device(serial)
    # If disable is a blocking call, consider running it in a threadpool.
    await run_in_threadpool(device.disable)
    return await get_status(serial)


@app.post("/api/device/{serial}/power", response_model=StatusResponse)
async def set_power(serial: str, request: SetPowerRequest):
    """Set the power of the device."""
    device = get_device(serial)
    # Set power (if this is blocking, run it in a threadpool)
    device.power = request.power
    return await get_status(serial)


# -----------------------------------------------------------------------------
# WebSocket endpoint
#
# In this version, each device record holds a single publisher task that
# runs as long as there is at least one active connection.
# -----------------------------------------------------------------------------
@app.websocket("/ws/device/{serial}")
async def device_ws(websocket: WebSocket, serial: str):
    # Ensure the device exists.
    if serial not in DEVICES:
        serials = get_cohrhops_manager().discover()
        if serial not in serials:
            raise HTTPException(status_code=404, detail=f"Device with serial {serial} not found.")
        DEVICES[serial] = DeviceRecord(GenesisMX(serial), wsManager())
    record = DEVICES[serial]
    ws_manager = record.socket

    await ws_manager.connect(websocket)

    # If there isn’t already a running publisher for this device, create one.
    if record.publisher_task is None or record.publisher_task.done():
        record.publisher_task = asyncio.create_task(device_status_publisher(ws_manager, serial))

    try:
        # Keep the connection open.
        # (If you expect messages from the client, process them here.)
        while True:
            # For example, simply wait for pings or messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for device {serial}.")
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for device {serial}: {e}")
        ws_manager.disconnect(websocket)
    # Note: we do not cancel the shared publisher here because other clients
    # might still be connected. The publisher itself will exit if there are no
    # active connections.


# -----------------------------------------------------------------------------
# Background publisher task for a device.
#
# This task will check the active connections in the wsManager and send a full
# update every 10 iterations and a quick power update otherwise.
# -----------------------------------------------------------------------------
async def device_status_publisher(ws_manager: wsManager, serial: str):
    counter = 0
    try:
        while True:
            # If no clients remain, exit the loop.
            if not ws_manager.active_connections:
                logger.info(f"No active connections for device {serial}, stopping publisher.")
                break

            if counter % 10 == 0:
                # Retrieve the full status in a threadpool.
                status = await run_in_threadpool(get_device_status, serial)
                full_update = {
                    "type": "full_status",
                    "data": status.model_dump(),  # using Pydantic's model_dump() for complete status
                }
                await ws_manager.broadcast(full_update)
            else:
                # Retrieve power status via threadpool to avoid blocking.
                power = await run_in_threadpool(get_device_power, serial)
                power_update = {
                    "type": "power_update",
                    "data": {"value": power.value, "setpoint": power.setpoint},
                }
                await ws_manager.broadcast(power_update)
            counter += 1
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info(f"Publisher for device {serial} cancelled.")
    except Exception as e:
        logger.error(f"Error in publisher for device {serial}: {e}")


# -----------------------------------------------------------------------------
# Serve static files (e.g. the Single Page Application).
# -----------------------------------------------------------------------------
frontend_build_dir = Path(__file__).parent / "frontend" / "build"
app.mount("/", StaticFiles(directory=frontend_build_dir, html=True), name="app")


def run():
    try:
        uvicorn.run(app, log_level="info")
    except KeyboardInterrupt:
        print("Shutdown requested. Exiting...")


if __name__ == "__main__":
    module_name = Path(__file__).stem
    try:
        uvicorn.run(f"{module_name}:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down.")
