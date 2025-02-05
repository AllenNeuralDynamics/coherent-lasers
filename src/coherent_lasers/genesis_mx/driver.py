from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
import logging
import random
from coherent_lasers.genesis_mx.commands import (
    ReadCmds,
    WriteCmds,
    OperationMode,
    Alarms,
)
from coherent_lasers.hops import HOPSDevice
from ..hops.lib import HOPSException


@dataclass(frozen=True)
class GenesisMXTempMetric:
    temp: float
    voltage: float


@dataclass
class GenesisMXTempMetrics:
    main: GenesisMXTempMetric
    etalon: GenesisMXTempMetric
    brf: GenesisMXTempMetric
    shg: GenesisMXTempMetric


@dataclass(frozen=True)
class GenesisMXHeadInfo:
    serial: str
    type: str
    hours: str
    board_revision: str
    dio_status: str


class GenesisMXHeadType(StrEnum):
    """Head types for Genesis MX lasers.
    - used in determining the unit factor for power readings and write commands.
    """

    MINIX = "MiniX"
    MINI00 = "Mini00"


@dataclass(frozen=True)
class GenesisMXEnableLoop:
    software: bool
    interlock: bool
    key: bool

    @property
    def enabled(self) -> bool:
        return self.software and self.interlock and self.key

    @property
    def ready(self) -> bool:
        return self.interlock and self.key and not self.software

    def __repr__(self) -> str:
        return (
            f"Software: {self.software}, Interlock: {self.interlock}, Key: {self.key}"
        )


class GenesisMX:
    def __init__(self, serial: str, logger: logging.Logger | None = None) -> None:
        self.log = logger if logger else logging.getLogger(f"{__name__}.{serial}")
        self.serial = serial
        self.hops = HOPSDevice(self.serial)
        if not self.hops:
            raise ValueError(f"Failed to initialize laser: {self.serial}")
        self.remote_control = True
        # self.disable()
        self._unit_factor = 1000 if self.head.type == GenesisMXHeadType.MINIX else 1

    @property
    def mode(self) -> OperationMode:
        """Get the current mode of the laser: current mode or photomode."""
        mode_value = self.send_read_command(ReadCmds.CURRENT_MODE)
        return OperationMode(int(mode_value))

    @mode.setter
    def mode(self, value: OperationMode) -> None:
        """Set the mode of the laser."""
        self.send_write_command(WriteCmds.SET_MODE, value.value)

    @property
    def power_mw(self) -> float:
        """Get the current power of the laser."""
        return self.send_read_float_command(ReadCmds.POWER) * self._unit_factor

    @power_mw.setter
    def power_mw(self, value: float) -> None:
        """Set the power of the laser."""
        value = value / self._unit_factor
        self.send_write_command(WriteCmds.SET_POWER, value)
        if not self.enable_loop.enabled:
            self.log.warning(
                f"Attempting to set power to {value} mW while laser is disabled."
            )

    @property
    def power_setpoint_mw(self) -> float:
        """Get the current power setpoint of the laser."""
        return (
            float(self.send_read_command(ReadCmds.POWER_SETPOINT)) * self._unit_factor
        )

    @property
    def ldd_current(self) -> float:
        """
        Get the LDD current of the laser.

        Measures the current supplied to the Laser Diode Driver (LDD).
        """
        return float(self.send_read_command(ReadCmds.LDD_CURRENT))

    @property
    def ldd_current_limit(self) -> float:
        """
        Get the LDD current limit of the laser.

        Measures the maximum current limit set for the Laser Diode Driver (LDD).
        """
        return float(self.send_read_command(ReadCmds.LDD_CURRENT_LIMIT))

    @property
    def enable_loop(self) -> GenesisMXEnableLoop:
        return GenesisMXEnableLoop(
            software=self.software_switch,
            interlock=self.interlock,
            key=self.key_switch,
        )

    @property
    def software_switch(self) -> bool:
        try:
            return self.send_read_bool_command(ReadCmds.SOFTWARE_SWITCH_STATE)
        except HOPSException:
            return False

    @property
    def interlock(self) -> bool:
        try:
            return self.send_read_bool_command(ReadCmds.INTERLOCK_STATUS)
        except HOPSException:
            return False

    @property
    def key_switch(self) -> bool:
        try:
            return self.send_read_bool_command(ReadCmds.KEY_SWITCH_STATE)
        except HOPSException:
            return False

    @property
    def remote_control(self) -> bool:
        try:
            return self.send_read_bool_command(ReadCmds.REMOTE_CONTROL_STATUS)
        except HOPSException:
            return True

    @remote_control.setter
    def remote_control(self, value: bool) -> None:
        try:
            self.send_write_command(WriteCmds.SET_REMOTE_CONTROL, value)
        except HOPSException:
            pass

    @property
    def analog_input(self) -> bool:
        try:
            return self.send_read_bool_command(ReadCmds.ANALOG_INPUT_STATUS)
        except HOPSException:
            return False

    @analog_input.setter
    def analog_input(self, value: bool) -> None:
        try:
            self.send_write_command(WriteCmds.SET_ANALOG_INPUT, value)
        except HOPSException:
            pass

    def enable(self) -> GenesisMXEnableLoop:
        """Enable the laser."""
        self.send_write_command(WriteCmds.SET_SOFTWARE_SWITCH, 1)
        return self.enable_loop

    def disable(self) -> GenesisMXEnableLoop:
        """Disable the laser."""
        self.send_write_command(WriteCmds.SET_SOFTWARE_SWITCH, 0)
        return self.enable_loop

    @property
    def is_ldd_enabled(self) -> bool:
        """
        Get the LDD enable state of the laser.

        Reads whether the Laser Diode Driver (LDD) is enabled or disabled.
        """
        return self.send_read_bool_command(ReadCmds.LDD_ENABLE_STATE)

    # Information

    @cached_property
    def head(self) -> GenesisMXHeadInfo:
        """Get the laser head information."""
        try:
            dio_status = self.send_read_command(ReadCmds.HEAD_DIO_STATUS)
        except HOPSException:
            dio_status = "N/A"
        return GenesisMXHeadInfo(
            serial=self.send_read_command(ReadCmds.HEAD_SERIAL),
            type=self.send_read_command(ReadCmds.HEAD_TYPE),
            hours=self.send_read_command(ReadCmds.HEAD_HOURS),
            board_revision=self.send_read_command(ReadCmds.HEAD_BOARD_REVISION),
            dio_status=dio_status,
        )

    @property
    def alarms(self) -> list[Alarms]:
        """Get the list of active alarms based on the fault code."""
        fault_code_value = int(self.send_read_command(ReadCmds.FAULT_CODE), 16)
        faults = Alarms.from_code(fault_code_value)
        return faults

    @property
    def temperature_c(self) -> float:
        """
        Get the main temperature of the laser.

        Description: Measures the temperature of the main thermoelectric cooler (TEC) that regulates
        the overall temperature of the laser head to ensure optimal performance and stability.
        """
        try:
            return self.send_read_float_command(ReadCmds.MAIN_TEMPERATURE)
        except HOPSException:
            return 0.0

    @property
    def main_tec_drive_v(self) -> float:
        """
        Get the main TEC drive voltage of the laser.

        Measures the drive voltage of the main thermoelectric cooler (TEC), which regulates the
        overall temperature of the laser head.
        """
        try:
            return self.send_read_float_command(ReadCmds.MAIN_TEC_DRIVE)
        except HOPSException:
            return 0.0

    @property
    def shg_temperature_c(self) -> float:
        """
        Get the SHG temperature of the laser in degrees Celsius.

        Measures the temperature of the Second Harmonic Generation (SHG) heater. The SHG heater is crucial for
        maintaining the proper temperature for efficient frequency doubling processes that convert
        the laser light to the desired wavelength.
        """
        try:
            return self.send_read_float_command(ReadCmds.SHG_TEMPERATURE)
        except HOPSException:
            return 0.0

    @property
    def shg_heater_drive_v(self) -> float:
        """Get the SHG heater drive voltage of the laser."""
        try:
            return self.send_read_float_command(ReadCmds.SHG_HEATER_DRIVE)
        except HOPSException:
            return 0.0

    @property
    def brf_temperature_c(self) -> float:
        """
        Get the BRF temperature of the laser in degrees Celsius.

        Measures the temperature of the Beam Reference Frequency (BRF) heater. The BRF heater is essential for
        maintaining the proper temperature for the frequency reference of the laser.
        """
        try:
            return self.send_read_float_command(ReadCmds.BRF_TEMPERATURE)
        except HOPSException:
            return 0.0

    @property
    def brf_heater_drive_v(self) -> float:
        """Get the BRF heater drive voltage of the laser."""
        try:
            return self.send_read_float_command(ReadCmds.BRF_HEATER_DRIVE)
        except HOPSException:
            return 0.0

    @property
    def etalon_temperature_c(self) -> float:
        """
        Get the etalon temperature of the laser in degrees Celsius.

        Measures the temperature of the etalon heater. The etalon heater is crucial for maintaining the proper
        temperature for the etalon, which is used to stabilize the laser wavelength.
        """
        try:
            return self.send_read_float_command(ReadCmds.ETALON_TEMPERATURE)
        except HOPSException:
            return 0.0

    @property
    def etalon_heater_drive_v(self) -> float:
        """Get the etalon heater drive voltage of the laser."""
        try:
            return self.send_read_float_command(ReadCmds.ETALON_HEATER_DRIVE)
        except HOPSException:
            return 0.0

    # Commands

    def send_write_command(
        self, cmd: WriteCmds, new_value: float | None = None
    ) -> None:
        """Send a write command to the laser."""
        self.hops.send_command(f"{cmd.value}{new_value}")

    def send_read_command(self, cmd: ReadCmds) -> str:
        """Send a read command to the laser."""
        return self.hops.send_command(cmd.value)

    def send_read_bool_command(self, cmd: ReadCmds) -> bool:
        """Send a read command to the laser."""
        OK = {1, "1"}
        return self.send_read_command(cmd).strip() in OK

    def send_read_float_command(self, cmd: ReadCmds) -> float:
        """Send a read command to the laser."""
        return float(self.send_read_command(cmd).strip())

    def close(self) -> None:
        self.power_mw = 0.0
        self.hops.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception as e:
            self.log.debug(f"Error closing laser {self.serial}: {e}")


class MockGenesisMX:
    def __init__(self, serial: str, logger: logging.Logger | None = None) -> None:
        self.log = logger if logger else logging.getLogger(f"{__name__}.{serial}")
        self.serial = serial
        self._power_mw = 0.0
        self._mode = OperationMode.PHOTO

        self._software_switch = False
        self._interlock = True
        self._key = True
        self._remote_control_enable = True
        self._analog_input_enable = False
        self._head = GenesisMXHeadInfo(
            serial=serial,
            type=GenesisMXHeadType.MINIX,
            hours=str(random.randint(100, 1000)),
            board_revision="1.0",
            dio_status="OK",
        )
        self._alarms = []

    @property
    def mode(self) -> OperationMode:
        """Get the current mode of the laser: current mode or photomode."""
        return self._mode

    @mode.setter
    def mode(self, value: OperationMode) -> None:
        """Set the mode of the laser."""
        self._mode = value

    @property
    def power_mw(self) -> float:
        """Get the current power of the laser."""
        if self.enable_loop.enabled:
            return random.gauss(self._power_mw, 0.25)
        return random.gauss(1.5, 0.15)

    @power_mw.setter
    def power_mw(self, value: float) -> None:
        """Set the power of the laser."""
        if not self.enable_loop.enabled:
            self.log.warning(
                f"Attempting to set power to {value} mW while laser is disabled."
            )
        self._power_mw = value

    @property
    def power_setpoint_mw(self) -> float:
        """Get the current power setpoint of the laser."""
        return self._power_mw

    @property
    def ldd_current(self) -> float:
        return 8 + self.power_mw / 900

    @property
    def ldd_current_limit(self) -> float:
        return 9 + 1000 / 900

    @property
    def enable_loop(self) -> GenesisMXEnableLoop:
        return GenesisMXEnableLoop(
            software=self._software_switch,
            interlock=self._interlock,
            key=self._key,
        )

    @property
    def software_switch(self) -> bool:
        return self._software_switch

    @property
    def interlock(self) -> bool:
        return self._interlock

    @property
    def key_switch(self) -> bool:
        return self._key

    @property
    def remote_control(self) -> bool:
        return self._remote_control_enable

    @remote_control.setter
    def remote_control(self, value: bool) -> None:
        self._remote_control_enable = value

    @property
    def analog_input(self) -> bool:
        return self._analog_input_enable

    @analog_input.setter
    def analog_input(self, value: bool) -> None:
        self._analog_input_enable = value

    def enable(self) -> GenesisMXEnableLoop:
        """Enable the laser."""
        self._software_switch = True
        return self.enable_loop

    def disable(self) -> GenesisMXEnableLoop:
        """Disable the laser."""
        self._software_switch = False
        return self.enable_loop

    @property
    def is_ldd_enabled(self) -> bool:
        return True

    @property
    def head(self) -> GenesisMXHeadInfo:
        return self._head

    @property
    def alarms(self) -> list[Alarms]:
        return self._alarms

    @property
    def temperature_c(self) -> float:
        return random.uniform(20.0, 30.0)

    @property
    def main_tec_drive_v(self) -> float:
        return random.uniform(0.0, 1.0)

    @property
    def shg_temperature_c(self) -> float:
        return random.uniform(20.0, 30.0)

    @property
    def shg_heater_drive_v(self) -> float:
        return random.uniform(0.0, 1.0)

    @property
    def brf_temperature_c(self) -> float:
        return random.uniform(20.0, 30.0)

    @property
    def brf_heater_drive_v(self) -> float:
        return random.uniform(0.0, 1.0)

    @property
    def etalon_temperature_c(self) -> float:
        return random.uniform(20.0, 30.0)

    @property
    def etalon_heater_drive_v(self) -> float:
        return random.uniform(0.0, 1.0)

    def close(self) -> None:
        pass
