import asyncio
import logging
from functools import wraps
from typing import TypeAlias

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from coherent_lasers.genesis_mx.commands import ReadCmds
from coherent_lasers.genesis_mx.driver import GenesisMX, MockGenesisMX
from coherent_lasers.hops.lib import get_hops_manager

GENESIS_MX_HEADTYPES = {"MiniX", "Mini00"}


class WebSocketManager:
    def __init__(self):
        self.clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.clients.remove(websocket)

    async def broadcast(self, message: dict):
        for client in self.clients:
            try:
                await client.send_json(message)
            except WebSocketDisconnect:
                self.clients.remove(client)

    async def shutdown(self):
        for client in self.clients:
            await client.close()


def handle_exceptions(endpoint_function):
    @wraps(endpoint_function)
    async def wrapper(*args, **kwargs):
        try:
            return await endpoint_function(*args, **kwargs)
        except ValueError as ve:
            print(f"ValueError: {ve}")
            raise HTTPException(status_code=400, detail=str(ve))
        except KeyError as ke:
            print(f"KeyError: {ke}")
            raise HTTPException(status_code=404, detail=str(ke))
        except Exception as e:
            print(f"Exception: {e}")
            # General exception handling
            raise HTTPException(status_code=500, detail=str(e))

    return wrapper


class GenesisMXHeadInfoModel(BaseModel):
    serial: str
    type: str
    hours: str
    board_revision: str
    dio_status: str


class GenesisMXSignals(BaseModel):
    power: float
    powerSetpoint: float
    lddCurrent: float
    lddCurrentLimit: float
    mainTemperature: float
    shgTemperature: float
    brfTemperature: float
    etalonTemperature: float


class GenesisMXPower(BaseModel):
    power: float
    powerSetpoint: float


class GenesisMXFlags(BaseModel):
    interlock: bool
    keySwitch: bool
    softwareSwitch: bool
    remoteControl: bool
    analogInput: bool


class GenesisMXModel(BaseModel):
    head: GenesisMXHeadInfoModel
    signals: GenesisMXSignals
    flags: GenesisMXFlags


MessageData: TypeAlias = (
    dict[str, GenesisMXSignals] | dict[str, GenesisMXPower] | dict[str, GenesisMXFlags]
)


class BaseMessage(BaseModel):
    type: str
    request_id: str | None = None
    data: MessageData | None = None


# class SignalsMessage(BaseMessage):
#     type: str = "signals"
#     data: dict[str, GenesisMXSignals] | dict[str, GenesisMXPower]


# class FlagsMessage(BaseMessage):
#     type: str = "flags"
#     data: dict[str, GenesisMXFlags]


class GenesisMXRouter(APIRouter):
    _manager = get_hops_manager()

    def __init__(self, num_mock_lasers: int = 0):
        super().__init__(prefix="/genesis-mx")
        self.log = logging.getLogger("HOPSRouter")
        serials = self._manager._handles.values()
        self.lasers: dict[str, GenesisMX | MockGenesisMX] = {}
        self.clients: set[WebSocket] = set()
        # self.ws_manager = WebSocketManager()
        self._power_interval = 0.05
        self._signal_interval = 10.0
        self._flags_interval = 1.0
        self._power_broadcast = None
        self._signal_broadcast = None
        self._flags_broadcast = None
        self._broadcast_tasks = []

        for serial in serials:
            try:
                laser = GenesisMX(serial)
                response = laser.send_read_command(ReadCmds.HEAD_TYPE)
                if response in GENESIS_MX_HEADTYPES:
                    self.lasers[serial] = laser
                else:
                    self.log.warning(
                        f"Device {serial} is not a Genesis MX laser. Skipping."
                    )
            except Exception as e:
                self.log.warning(f"Failed to initialize device {serial}: {e}")
                continue

        for i in range(num_mock_lasers):
            serial = f"mock-laser-{i}"
            self.lasers[serial] = MockGenesisMX(serial)

        @self.websocket("/")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.clients.add(websocket)
            # await self.ws_manager.connect(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    await websocket.send_text(f"Message text was: {data}")
            except WebSocketDisconnect:
                pass
            finally:
                self.clients.remove(websocket)
                # await self.ws_manager.disconnect(websocket)

        @self.on_event("shutdown")
        async def shutdown_event():
            await self.stop_broadcast_tasks()
            for websocket in self.clients:
                await websocket.close(code=1001, reason="Server shutdown")

        @self.get("/")
        @handle_exceptions
        async def get_lasers() -> list[GenesisMXModel]:
            return self._get_all_laser_info()

        @self.get("/devices")
        @handle_exceptions
        async def get_devices() -> list[str]:
            return list(self._manager._handles.values())

        @self.get("/serials")
        @handle_exceptions
        async def get_serials() -> list[str]:
            return list(self.lasers.keys())

        @self.put("/power")
        @handle_exceptions
        async def set_laser_power(serial: str, value: float):
            if serial not in self.lasers:
                raise HTTPException(status_code=404, detail="Laser not found")
            laser = self.lasers[serial]
            laser.power_mw = value
            await self.broadcast_power()

        @self.put("/enable")
        @handle_exceptions
        async def enable_laser(serial: str):
            if serial not in self.lasers:
                raise HTTPException(status_code=404, detail="Laser not found")
            self.lasers[serial].enable()
            await self.broadcast_flags()

        @self.put("/disable")
        @handle_exceptions
        async def disable_laser(serial: str):
            if serial not in self.lasers:
                raise HTTPException(status_code=404, detail="Laser not found")
            self.lasers[serial].disable()
            await self.broadcast_flags()

        @self.put("/remote")
        @handle_exceptions
        async def set_remote_control(serial: str, value: bool):
            if serial not in self.lasers:
                raise HTTPException(status_code=404, detail="Laser not found")
            laser = self.lasers[serial]
            laser.remote_control_enable = value
            await self.broadcast_flags()

        @self.get("/signals")
        @handle_exceptions
        async def get_laser_signals(serial: str) -> GenesisMXSignals:
            if serial not in self.lasers:
                raise HTTPException(status_code=404, detail="Laser not found")
            return self._get_laser_signals(self.lasers[serial])

        @self.get("/flags")
        @handle_exceptions
        async def get_laser_flags(serial: str) -> GenesisMXFlags:
            if serial not in self.lasers:
                raise HTTPException(status_code=404, detail="Laser not found")
            return self._get_laser_flags(self.lasers[serial])

    async def broadcast(self, message: BaseMessage):
        for client in self.clients:
            await client.send_json(message.model_dump())

    async def broadcast_items(self, msg_type: str, data: MessageData):
        # if self.lasers and self.ws_manager.clients:
        if self.lasers and self.clients:
            message = BaseMessage(type=msg_type, data=data)
            # await self.ws_manager.broadcast(message.model_dump())
            await self.broadcast(message)

    async def broadcast_power(self):
        await self.broadcast_items("signals", self._get_all_laser_powers())

    async def broadcast_signals(self):
        await self.broadcast_items("signals", self._get_all_laser_signals())

    async def broadcast_flags(self):
        await self.broadcast_items("flags", self._get_all_laser_flags())

    async def scheduled_broadcast(
        self, msg_type: str, data: MessageData, interval: float
    ):
        while True:
            try:
                await self.broadcast_items(msg_type, data)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def start_broadcast_tasks(self):
        self._broadcast_tasks = [
            asyncio.create_task(
                self.scheduled_broadcast(
                    msg_type="signals",
                    data=self._get_all_laser_powers(),
                    interval=self._power_interval,
                )
            ),
            asyncio.create_task(
                self.scheduled_broadcast(
                    msg_type="signals",
                    data=self._get_all_laser_signals(),
                    interval=self._signal_interval,
                )
            ),
            asyncio.create_task(
                self.scheduled_broadcast(
                    msg_type="flags",
                    data=self._get_all_laser_flags(),
                    interval=self._flags_interval,
                )
            ),
        ]

    async def stop_broadcast_tasks(self):
        for task in self._broadcast_tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except WebSocketDisconnect:
                    pass

    # async def broadcast_power(self):

    #     if self.lasers and self.ws_manager.clients:
    #         powers = {
    #             serial: GenesisMXPower(
    #                 power=laser.power_mw, powerSetpoint=laser.power_setpoint_mw
    #             )
    #             for serial, laser in self.lasers.items()
    #         }
    #         message = SignalsMessage(data=powers)
    #         await self.ws_manager.broadcast(message.model_dump())

    # async def broadcast_signals(self):
    #     if self.lasers and self.ws_manager.clients:
    #         signals = {
    #             serial: self._get_laser_signals(laser)
    #             for serial, laser in self.lasers.items()
    #         }
    #         message = SignalsMessage(data=signals)
    #         await self.ws_manager.broadcast(message.model_dump())

    # async def broadcast_flags(self):
    #     if self.lasers and self.ws_manager.clients:
    #         flags = {
    #             serial: self.get_laser_flags(laser)
    #             for serial, laser in self.lasers.items()
    #         }
    #         message = FlagsMessage(data=flags)
    #         await self.ws_manager.broadcast(message.model_dump())

    # async def start_broadcast_tasks(self):
    #     async def power_broadcast():
    #         while True:
    #             await self.broadcast_power()
    #             await asyncio.sleep(self._power_interval)

    #     self._power_broadcast = asyncio.create_task(power_broadcast())

    #     async def signals_broadcast():
    #         while True:
    #             await self.broadcast_signals()
    #             await asyncio.sleep(self._signal_interval)

    #     self._signal_broadcast = asyncio.create_task(signals_broadcast())

    #     async def flags_broadcast():
    #         while True:
    #             await self.broadcast_flags()
    #             await asyncio.sleep(self._flags_interval)

    #     self._flags_broadcast = asyncio.create_task(flags_broadcast())

    # async def stop_broadcast_tasks(self):
    #     for task in [
    #         self._power_broadcast,
    #         self._signal_broadcast,
    #         self._flags_broadcast,
    #     ]:
    #         if task:
    #             task.cancel()
    #             try:
    #                 await task
    #             except asyncio.CancelledError:
    #                 pass

    def _get_all_laser_info(self) -> list[GenesisMXModel]:
        info = []
        for laser in self.lasers.values():
            info.append(
                GenesisMXModel(
                    head=self._get_laser_head_info(laser),
                    flags=self._get_laser_flags(laser),
                    signals=self._get_laser_signals(laser),
                )
            )
        return info

    @staticmethod
    def _get_laser_head_info(
        laser: GenesisMX | MockGenesisMX,
    ) -> GenesisMXHeadInfoModel:
        head_info = laser.head
        return GenesisMXHeadInfoModel(
            serial=head_info.serial,
            type=head_info.type,
            hours=head_info.hours,
            board_revision=head_info.board_revision,
            dio_status=head_info.dio_status,
        )

    @staticmethod
    def _get_laser_signals(
        laser: GenesisMX | MockGenesisMX,
    ) -> GenesisMXSignals:
        return GenesisMXSignals(
            power=laser.power_mw,
            powerSetpoint=laser.power_setpoint_mw,
            lddCurrent=laser.ldd_current,
            lddCurrentLimit=laser.ldd_current_limit,
            mainTemperature=laser.temperature_c,
            shgTemperature=laser.shg_temperature_c,
            brfTemperature=laser.brf_temperature_c,
            etalonTemperature=laser.etalon_temperature_c,
        )

    @staticmethod
    def _get_laser_flags(
        laser: GenesisMX | MockGenesisMX,
    ) -> GenesisMXFlags:
        return GenesisMXFlags(
            interlock=laser.enable_loop.interlock,
            keySwitch=laser.enable_loop.key,
            softwareSwitch=laser.enable_loop.software,
            remoteControl=laser.remote_control_enable,
            analogInput=laser.analog_input_enable,
        )

    @staticmethod
    def _get_laser_power(
        laser: GenesisMX | MockGenesisMX,
    ) -> GenesisMXPower:
        return GenesisMXPower(
            power=laser.power_mw,
            powerSetpoint=laser.power_setpoint_mw,
        )

    def _get_all_laser_powers(self) -> dict[str, GenesisMXPower]:
        return {
            serial: self._get_laser_power(laser)
            for serial, laser in self.lasers.items()
        }

    def _get_all_laser_signals(self) -> dict[str, GenesisMXSignals]:
        return {
            serial: self._get_laser_signals(laser)
            for serial, laser in self.lasers.items()
        }

    def _get_all_laser_flags(self) -> dict[str, GenesisMXFlags]:
        return {
            serial: self._get_laser_flags(laser)
            for serial, laser in self.lasers.items()
        }
