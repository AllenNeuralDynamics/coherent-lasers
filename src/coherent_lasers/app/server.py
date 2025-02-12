import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import asynccontextmanager, run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import your GenesisMX class and HOPS manager factory.
from coherent_lasers.genesis_mx import GenesisMX, GenesisMXMock
from coherent_lasers.genesis_mx.hops import get_cohrhops_manager

from .messaging import MessageEnvelope, PeriodicTask, PubSubHub, WebSocketHub

logger = logging.getLogger("laser_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

pub_sub_hub = WebSocketHub()


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
    power: PowerStatus | None
    temperature: float | None
    current: float | None
    mode: int | None
    alarms: list[str] | None


# ----------------------------------------------------------------------------------------------------------------------
# State management classes: DeviceState and ApplicationState.
# ----------------------------------------------------------------------------------------------------------------------
class DeviceState:
    FAST_POLL_INTERVAL = 0.15
    SLOW_POLL_INTERVAL = 5.0
    FAST_PUBLISH_INTERVAL = 0.0333
    SLOW_PUBLISH_INTERVAL = 5.0

    def __init__(self, instance: GenesisMX | GenesisMXMock, publisher: PubSubHub):
        self.instance = instance
        self.publisher = publisher
        self.power: PowerStatus | None = None
        self.status: StatusResponse | None = None

        self.periodic_tasks: list[PeriodicTask] = []
        self.periodic_tasks.append(PeriodicTask(self.update_power_status, self.FAST_POLL_INTERVAL))
        self.periodic_tasks.append(PeriodicTask(self.update_full_status, self.SLOW_POLL_INTERVAL))
        self.periodic_tasks.append(PeriodicTask(self.publish_power_updates, self.FAST_PUBLISH_INTERVAL))
        self.periodic_tasks.append(PeriodicTask(self.publish_full_status_updates, self.SLOW_PUBLISH_INTERVAL))

    @property
    def serial(self) -> str:
        return self.instance.serial

    async def enable(self):
        await run_in_threadpool(self.instance.enable)
        await self.update_power_status()

    async def disable(self):
        await run_in_threadpool(self.instance.disable)
        await self.update_power_status()

    def run(self):
        for task in self.periodic_tasks:
            task.start()

    def shutdown(self):
        for task in self.periodic_tasks:
            task.stop()

    async def update_power_status(self) -> PowerStatus:
        self.power = await run_in_threadpool(
            lambda: PowerStatus(value=self.instance.power.value, setpoint=self.instance.power.setpoint)
        )
        return self.power

    async def update_full_status(self) -> StatusResponse:
        self.status = await run_in_threadpool(
            lambda: StatusResponse(
                remote_control=self.instance.remote_control,
                key_switch=self.instance.key_switch,
                interlock=self.instance.interlock,
                software_switch=self.instance.software_switch,
                power=self.power,
                temperature=self.instance.temperature,
                current=self.instance.current,
                mode=self.instance.mode.value if self.instance.mode else None,
                alarms=self.instance.alarms,
            )
        )
        return self.status

    async def publish_power_updates(self):
        if not self.power:
            await self.update_power_status()
        if self.power:
            msg = MessageEnvelope(topic=self.serial, subtopic="power_update", payload=self.power.model_dump())
            await self.publisher.broadcast(msg.topic, msg)

    async def publish_full_status_updates(self):
        if not self.status:
            await self.update_full_status()
        if self.status:
            msg = MessageEnvelope(topic=self.serial, subtopic="full_status", payload=self.status.model_dump())
            await self.publisher.broadcast(msg.topic, msg)


class ApplicationState:
    def __init__(self, publisher: PubSubHub):
        self.publisher = pub_sub_hub
        self.devices: dict[str, DeviceState] = {}
        self.logger = logging.getLogger("app_state")

    @property
    def serials(self) -> list[str]:
        return list(self.devices.keys())

    def shutdown(self):
        for device in self.devices.values():
            device.shutdown()

    def discover(self, mock: bool = False):
        self.devices.clear()
        try:
            for serial in get_cohrhops_manager().discover():
                instance = GenesisMX(serial)
                device_state = DeviceState(instance, self.publisher)
                device_state.run()
                self.devices[serial] = device_state
            self.logger.info(f"Discovered devices: {list(self.devices.keys())}")
        except Exception as e:
            self.logger.error(f"Discovery failed: {e}")
            if mock:
                self.logger.info("Using mock devices for testing.")
                self.devices.update(self._generate_mock_devices())
                for device in self.devices.values():
                    device.run()

    def get_device_instance(self, serial: str) -> GenesisMX | GenesisMXMock:
        if serial not in self.devices:
            raise HTTPException(status_code=404, detail=f"Device with serial {serial} not found.")
        return self.devices[serial].instance

    def get_device_state(self, serial: str) -> DeviceState:
        if serial not in self.devices:
            raise HTTPException(status_code=404, detail=f"Device with serial {serial} not found.")
        return self.devices[serial]

    def _generate_mock_devices(self, num: int = 3) -> dict[str, DeviceState]:
        colors = ["RED", "GREEN", "BLUE"]
        serials = [f"{colors[i % len(colors)]}-GENESIS-MX-MOCK-{i}" for i in range(num)]
        return {serial: DeviceState(GenesisMXMock(serial), self.publisher) for serial in serials}


# ----------------------------------------------------------------------------------------------------------------------


# initialize the global app state
state = ApplicationState(pub_sub_hub)


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.discover()
    yield
    state.shutdown()


app = FastAPI(title="Laser Control API", version="0.1", lifespan=lifespan)
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# decorator to handle exceptions logging errors and returning 500
@app.exception_handler(Exception)
async def exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return HTTPException(status_code=500, detail="Internal Server Error")


# ----------------------------------------------------------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------------------------------------------------------
@app.post("/api/discover")
async def discover_devices(mock: bool = False) -> list[str]:
    """Discover devices and return their serial numbers."""
    state.discover(mock)
    return state.serials


@app.get("/api/devices", response_model=list[str])
async def list_devices(mock: bool = False) -> list[str]:
    """List all available device serial numbers."""
    if not state.serials:
        state.discover(mock)
    if not state.serials:
        raise HTTPException(status_code=404, detail="No devices discovered.")
    return state.serials


@app.get("/api/device/{serial}/status", response_model=StatusResponse)
async def get_status(serial: str):
    """Retrieve a detailed status report from the device."""
    return await state.get_device_state(serial).update_full_status()


@app.get("/api/device/{serial}/info", response_model=DeviceInfo)
async def get_info(serial: str):
    """Retrieve device info."""
    device = state.devices[serial].instance
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
    await state.get_device_state(serial).enable()
    return await get_status(serial)


@app.post("/api/device/{serial}/disable", response_model=StatusResponse)
async def disable_device(serial: str):
    """Disable the device."""
    await state.get_device_state(serial).disable()
    return await get_status(serial)


@app.post("/api/device/{serial}/power", response_model=StatusResponse)
async def set_power(serial: str, request: SetPowerRequest):
    """Set the power of the device."""
    state.get_device_instance(serial).power = request.power
    await state.get_device_state(serial).update_power_status()
    return await get_status(serial)


# ----------------------------------------------------------------------------------------------------------------------
# WebSocket endpoint
# ----------------------------------------------------------------------------------------------------------------------
@app.websocket("/ws")
async def shared_ws(websocket: WebSocket):
    conn = await pub_sub_hub.connect(websocket)
    try:
        while True:
            # Expect subscription messages, e.g., {"subscribe": ["device123", "device456"], "unsubscribe": ["device789"]}
            msg = await websocket.receive_json()
            if "subscribe" in msg:
                for topic in msg["subscribe"]:
                    if topic not in conn.subscribed_topics:
                        conn.subscribed_topics.append(topic)
                        logger.info(f"Client subscribed to topic: {topic}")
            if "unsubscribe" in msg:
                for topic in msg["unsubscribe"]:
                    if topic in conn.subscribed_topics:
                        conn.subscribed_topics.remove(topic)
                        logger.info(f"Client unsubscribed from topic: {topic}")
    except WebSocketDisconnect:
        logger.info("Shared websocket disconnected.")
        pub_sub_hub.disconnect(conn)
    except Exception as e:
        logger.error(f"Shared websocket error: {e}")
        pub_sub_hub.disconnect(conn)


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
