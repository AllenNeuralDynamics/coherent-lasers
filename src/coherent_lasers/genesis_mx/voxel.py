from coherent_lasers.genesis_mx.driver import GenesisMX
from coherent_lasers.genesis_mx.commands import OperationMode
from voxel.devices.laser.base import BaseLaser


INIT_POWER_MW = 10.0


class GenesisMXVoxelLaser(BaseLaser):
    def __init__(self, id: str, conn: str, wavelength: int) -> None:
        super().__init__(id)
        self._conn = conn
        try:
            self._inst = GenesisMX(serial=conn)
            assert self._inst.head.serial == conn
            self._inst.mode = OperationMode.PHOTO
        except AssertionError:
            raise ValueError(
                f"Error initializing laser {self.id}, serial number mismatch"
            )
        self.enable()
        self.power_setpoint_mw = INIT_POWER_MW
        self._wavelength = wavelength

    @property
    def wavelength(self) -> int:
        return self._wavelength

    def enable(self) -> None:
        if self._inst is None:
            self._inst = GenesisMX(serial=self._conn)
        self._inst.enable()

    def disable(self) -> None:
        self._inst.disable()

    def close(self) -> None:
        self.disable()

    @property
    def power_mw(self) -> float:
        return self._inst.power_mw

    @property
    def power_setpoint_mw(self) -> float:
        return self._inst.power_setpoint_mw

    @power_setpoint_mw.setter
    def power_setpoint_mw(self, value: float) -> None:
        self._inst.power_mw = value

    @property
    def temperature_c(self) -> float:
        """The temperature of the laser in degrees Celsius."""
        return self._inst.temperature_c
