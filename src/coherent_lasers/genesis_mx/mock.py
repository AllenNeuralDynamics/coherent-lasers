import logging
import random
from functools import cached_property

from .commands import OperationMode
from .base import GenesisMXInfo, LaserPower, LaserTemperature


class GenesisMXMock:
    def __init__(self, serial: str) -> None:
        self.log = logging.getLogger(__name__)
        self.serial = serial
        self._power_setpoint = 0
        self._remote_control = True
        self._analog_input = False
        self._software_switch = False
        self._mode = OperationMode.CURRENT

    @cached_property
    def info(self) -> GenesisMXInfo:
        return GenesisMXInfo(
            serial=self.serial,
            wavelength=561
            if self.serial.lower().startswith("green")
            else 488
            if self.serial.lower().startswith("blue")
            else 639,
            head_type="MiniX",
            head_hours=str(random.randint(0, 1000)),
            head_dio_status=None,  # Unreliable command
            head_board_revision="1.0",
        )

    @property
    def power(self) -> LaserPower:
        """Power and Power Setpoint in mW.
        :return: The power in mW or None if an error occurred.
        :rtype: LaserPower
        """
        value = random.gauss(mu=self._power_setpoint, sigma=0.1) if self.is_enabled else random.gauss(mu=0, sigma=0.1)
        return LaserPower(value=max(value, 0), setpoint=self._power_setpoint)

    @power.setter
    def power(self, power: float) -> None:
        """Set the power setpoint in mW.
        :param power: The power setpoint in mW.
        :type power: float
        """
        self._power_setpoint = power

    @property
    def current(self) -> float | None:
        """Current in mA."""
        return self.power.value or 0 / 1000 * random.uniform(1, 20) if self.power else None

    @property
    def remote_control(self) -> bool | None:
        """Whether remote control is enabled."""
        return self._remote_control

    @remote_control.setter
    def remote_control(self, state: bool) -> None:
        self._remote_control = state

    @property
    def key_switch(self) -> bool | None:
        """Key switch state."""
        return True

    @property
    def interlock(self) -> bool | None:
        """Interlock state."""
        return True

    @property
    def software_switch(self) -> bool | None:
        """Software switch state."""
        return self._software_switch

    @software_switch.setter
    def software_switch(self, state: bool) -> None:
        if not self.interlock or not self.key_switch:
            self.log.error(f"Cannot enable: interlock={self.interlock}, key_switch={self.key_switch}")
            return
        self._software_switch = state

    @property
    def is_enabled(self) -> bool | None:
        """Whether the laser is enabled."""
        return self.interlock and self.key_switch and self.software_switch

    def enable(self) -> None:
        """Enable the laser. - turns on the software switch. Requires interlock and key switch to be enabled."""
        self.software_switch = True

    def disable(self) -> None:
        """Disable the laser. - turns off the software switch."""
        self.software_switch = False

    @property
    def analog_input(self) -> bool | None:
        """Whether analog input control is enabled.
        :return: True if enabled, False if disabled, None if an error occurred.
        :rtype: bool | None
        """
        return self._analog_input

    @analog_input.setter
    def analog_input(self, state: bool) -> None:
        self._analog_input = state

    @property
    def temperature(self) -> float | None:
        """Main temperature in °C."""
        return random.uniform(20, 30)

    def get_temperatures(self, include_only: list[str] | None = None) -> LaserTemperature:
        """Get the temperatures of the laser.

        :param exclude: List of temperature types to exclude from the result.
        :return: A GenesisMXTemperature object containing the temperatures.
        """
        temp_types = ["main", "shg", "brf", "etalon"]
        include = include_only or temp_types
        return LaserTemperature(
            main=random.uniform(20, 30) if "main" in include else None,
            shg=random.uniform(20, 30) if "shg" in include else None,
            brf=random.uniform(20, 30) if "brf" in include else None,
            etalon=None,  # Command didn't work for MiniX and Mini00
        )

    @property
    def mode(self) -> OperationMode | None:
        """Supports CURRENT and PHOTO modes."""
        return self._mode

    @mode.setter
    def mode(self, mode: OperationMode) -> None:
        self._mode = mode

    @property
    def alarms(self) -> list[str] | None:
        """Get the list of active alarms based on the fault code."""
        return []

    def __repr__(self) -> str:
        return f"GenesisMX(serial={self.serial}, wavelength={self.info.wavelength}, head_type={self.info.head_type})"

    def close(self) -> None:
        """Close the connection to the laser."""
        pass

    # send commands helper functions
    # Not needed for the mock
