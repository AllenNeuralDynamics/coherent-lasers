from coherent_lasers.genesis_mx.driver import GenesisMX
from coherent_lasers.genesis_mx.commands import OperationModes
from voxel.devices.laser import BaseLaser

INIT_POWER_MW = 10.0


class GenesisMXVoxelLaser(BaseLaser):
    def __init__(self, id: str, conn: str):
        super().__init__(id)
        self._conn = conn
        self._inst = GenesisMX(serial=conn)
        try:
            assert self._inst.head["serial"] == conn
        except AssertionError:
            raise ValueError(f"Error initializing laser {self.id}, serial number mismatch")
        self._inst.mode = OperationModes.PHOTO
        self.enable()
        self.power_setpoint_mw = INIT_POWER_MW

    def enable(self):
        if self._inst is None:
            self._inst = GenesisMX(serial=self._conn)
        self._inst.enable()

    def disable(self):
        self._inst.disable()

    def close(self):
        self.disable()
        if not self._inst.is_enabled:
            self._inst = None

    @property
    def power_mw(self):
        return self._inst.power_mw

    @property
    def power_setpoint_mw(self):
        return self._inst.power_setpoint_mw

    @power_setpoint_mw.setter
    def power_setpoint_mw(self, value: float):
        self._inst.power_mw = value

    @property
    def temperature_c(self) -> float:
        """The temperature of the laser in degrees Celsius."""
        return self._inst.temperature_c
