from dataclasses import dataclass
from functools import cached_property
from typing import Protocol
from .commands import Alarm, OperationMode


@dataclass(frozen=True)
class GenesisMXInfo:
    serial: str
    wavelength: int
    head_type: str | None
    head_hours: str | None
    head_dio_status: str | None
    head_board_revision: str | None


@dataclass(frozen=True)
class LaserTemperature:
    main: float | None
    shg: float | None
    brf: float | None
    etalon: float | None


@dataclass(frozen=True)
class LaserPower:
    value: float | None
    setpoint: float | None

    @property
    def delta(self) -> float | None:
        if self.value is None or self.setpoint is None:
            return None
        return self.value - self.setpoint


class GenesisMXLaser(Protocol):
    @cached_property
    def info(self) -> GenesisMXInfo: ...

    @property
    def power(self) -> LaserPower:
        """Power and Power Setpoint in mW.
        :return: The power in mW or None if an error occurred.
        :rtype: LaserPower
        """
        ...

    @power.setter
    def power(self, power: float) -> None:
        """Set the power setpoint in mW.
        :param power: The power setpoint in mW.
        :type power: float
        """
        ...

    @property
    def current(self) -> float | None:
        """Current in mA."""
        ...

    @property
    def remote_control(self) -> bool | None:
        """Whether remote control is enabled."""
        ...

    @remote_control.setter
    def remote_control(self, state: bool) -> None: ...

    @property
    def key_switch(self) -> bool | None:
        """Key switch state."""
        ...

    @property
    def interlock(self) -> bool | None:
        """Interlock state."""
        ...

    @property
    def software_switch(self) -> bool | None:
        """Software switch state."""
        ...

    @software_switch.setter
    def software_switch(self, state: bool) -> None: ...

    @property
    def is_enabled(self) -> bool | None:
        """Whether the laser is enabled."""
        ...

    def enable(self) -> None:
        """Enable the laser. - turns on the software switch. Requires interlock and key switch to be enabled."""
        ...

    def disable(self) -> None:
        """Disable the laser. - turns off the software switch."""
        ...

    @property
    def analog_input(self) -> bool | None:
        """Whether analog input control is enabled.
        :return: True if enabled, False if disabled, None if an error occurred.
        :rtype: bool | None
        """
        ...

    @analog_input.setter
    def analog_input(self, state: bool) -> None: ...

    @property
    def temperature(self) -> float | None:
        """Main temperature in °C."""
        ...

    def get_temperatures(self, include_only: list[str] | None = None) -> LaserTemperature:
        """Get the temperatures of the laser.

        :param exclude: List of temperature types to exclude from the result.
        :return: A GenesisMXTemperature object containing the temperatures.
        """
        ...

    @property
    def mode(self) -> OperationMode | None:
        """Supports CURRENT and PHOTO modes."""
        ...

    @mode.setter
    def mode(self, mode: OperationMode) -> None: ...

    @property
    def alarms(self) -> list[Alarm] | None:
        """Get the list of active alarms based on the fault code."""
        ...
