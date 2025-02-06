from functools import cached_property

from attr import dataclass
from coherent_lasers.genesis_mx.commands import OperationMode, ReadWriteCmd, ReadCmd
from coherent_lasers.hops.cohrhops import CohrHOPSDevice, HOPSCommandException


@dataclass(frozen=True)
class GenesisMXInfo:
    serial: str
    wavelength: int
    head_type: str | None
    head_hours: str | None
    head_dio_status: str | None
    head_board_revision: str | None


@dataclass(frozen=True)
class GenesisMXTemperature:
    main: float | None
    shg: float | None
    brf: float | None
    etalon: float | None


class GenesisMX(CohrHOPSDevice):
    serial2wavelength = {"A": 488, "J": 561, "R": 639}
    head_type2unit_factor = {"MiniX": 1000, "Mini00": 1}

    def __init__(self, serial: str) -> None:
        super().__init__(serial=serial)

    @cached_property
    def info(self) -> GenesisMXInfo:
        return GenesisMXInfo(
            serial=self.serial,
            wavelength=self.serial2wavelength[self.serial[0]],
            head_type=self.send_read_command(ReadCmd.HEAD_TYPE),
            head_hours=self.send_read_command(ReadCmd.HEAD_HOURS),
            head_dio_status=self.send_read_command(ReadCmd.HEAD_DIO_STATUS),
            head_board_revision=self.send_read_command(ReadCmd.HEAD_BOARD_REVISION),
        )

    @cached_property
    def unit_factor(self) -> float:
        if head_type := self.info.head_type:
            return self.head_type2unit_factor.get(head_type, 1)
        return 1

    @property
    def power(self) -> float | None:
        """Power in mW."""
        if power := self.send_read_float_command(ReadCmd.POWER):
            return power / self.unit_factor
        return None

    @property
    def power_setpoint(self) -> float | None:
        """Power setpoint in mW."""
        if power_setpoint := self.send_read_float_command(ReadWriteCmd.POWER_SETPOINT):
            return power_setpoint / self.unit_factor
        return None

    @power_setpoint.setter
    def power_setpoint(self, power_setpoint: float) -> None:
        self.send_write_command(cmd=ReadWriteCmd.POWER_SETPOINT, value=power_setpoint * self.unit_factor)

    @property
    def current(self) -> float | None:
        """Current in mA."""
        return self.send_read_float_command(ReadCmd.CURRENT)

    @property
    def remote_control_status(self) -> bool | None:
        """Whether remote control is enabled."""
        return self.send_read_bool_command(ReadWriteCmd.REMOTE_CONTROL)

    @remote_control_status.setter
    def remote_control_status(self, state: bool) -> None:
        self.send_write_command(cmd=ReadWriteCmd.REMOTE_CONTROL, value=int(state))

    @property
    def key_switch_status(self) -> bool | None:
        """Key switch state."""
        return self.send_read_bool_command(ReadCmd.KEY_SWITCH_STATUS)

    @property
    def interlock_status(self) -> bool | None:
        """Interlock state."""
        return self.send_read_bool_command(ReadCmd.INTERLOCK_STATUS)

    @property
    def software_switch(self) -> bool | None:
        """Software switch state."""
        return self.send_read_bool_command(ReadWriteCmd.SOFTWARE_SWITCH)

    @software_switch.setter
    def software_switch(self, state: bool) -> None:
        if not self.interlock_status or not self.key_switch_status:
            self.log.error(f"Cannot enable: interlock={self.interlock_status}, key_switch={self.key_switch_status}")
            return
        self.send_write_command(cmd=ReadWriteCmd.SOFTWARE_SWITCH, value=int(state))

    @property
    def is_enabled(self) -> bool | None:
        """Whether the laser is enabled."""
        return self.interlock_status and self.key_switch_status and self.software_switch

    def enable(self) -> None:
        """Enable the laser. - turns on the software switch. Requires interlock and key switch to be enabled."""
        self.software_switch = True

    def disable(self) -> None:
        """Disable the laser. - turns off the software switch."""
        self.software_switch = False

    @property
    def analog_input_status(self) -> bool | None:
        """Whether analog input control is enabled."""
        return self.send_read_bool_command(ReadWriteCmd.ANALOG_INPUT)

    @analog_input_status.setter
    def analog_input_status(self, state: bool) -> None:
        self.send_write_command(cmd=ReadWriteCmd.ANALOG_INPUT, value=int(state))

    @property
    def temperature(self) -> float | None:
        """Main temperature in °C."""
        return self.send_read_float_command(ReadCmd.MAIN_TEMPERATURE)

    def get_temperatures(self, exclude: list[str] = []) -> GenesisMXTemperature:
        """Get the temperatures of the laser.

        :param exclude: List of temperature types to exclude from the result.
        :return: A GenesisMXTemperature object containing the temperatures.
        """
        return GenesisMXTemperature(
            main=self.send_read_float_command(ReadCmd.MAIN_TEMPERATURE) if "main" not in exclude else None,
            shg=self.send_read_float_command(ReadCmd.SHG_TEMPERATURE) if "shg" not in exclude else None,
            brf=self.send_read_float_command(ReadCmd.BRF_TEMPERATURE) if "brf" not in exclude else None,
            etalon=self.send_read_float_command(ReadCmd.ETALON_TEMPERATURE) if "etalon" not in exclude else None,
        )

    @property
    def mode(self) -> OperationMode | None:
        """Supports CURRENT and PHOTO modes."""
        if mode := self.send_read_int_command(ReadWriteCmd.MODE):
            return OperationMode(mode)
        return None

    @mode.setter
    def mode(self, mode: OperationMode) -> None:
        self.send_write_command(cmd=ReadWriteCmd.MODE, value=mode.value)

    def __repr__(self) -> str:
        return f"GenesisMX(serial={self.serial}, wavelength={self.info.wavelength}, head_type={self.info.head_type})"

    # send commands helper functions
    def send_write_command(self, cmd: ReadWriteCmd, value: float | int) -> float | None:
        """
        Sends a write command, then reads back the new value from the laser.

        :param cmd: The read/write command to send.
        :param value: The value to send with the command.
        :return: The newly-updated value from the laser if successful, None otherwise.
        """
        try:
            # 1. Write the new value
            self.send_command(command=cmd.write(value))

            # 2. Read back the updated value
            response_str = self.send_command(command=cmd.read())

            # 3. Attempt to parse the response as a float
            new_value = float(response_str)

            if new_value != value:
                self.log.warning(f"Write/readback mismatch: {value} != {new_value}")

            return new_value

        except (HOPSCommandException, ValueError) as e:
            self.log.error(f"Error during write or readback: {e}")
            return None

    def send_read_command(self, cmd: ReadCmd | ReadWriteCmd) -> str | None:
        """Send a read command to the laser.
        :param cmd: The command to send.
        :type cmd: GenesisMXCmd.Read
        :return: The response from the laser or None if an error occurred.
        :rtype: str | None
        """
        try:
            return self.send_command(command=cmd.read())
        except HOPSCommandException as e:
            self.log.error(f"Error: {e}")
            return None

    def send_read_bool_command(self, cmd: ReadCmd | ReadWriteCmd) -> bool | None:
        """Send a read command to the laser and return the response as a boolean.
        :param cmd: The command to send.
        :type cmd: GenesisMXCmd.Read
        :return: The response from the laser as a boolean or None if an error occurred.
        :rtype: bool | None
        """
        try:
            response = self.send_command(command=cmd.read())
            return response == "1"
        except HOPSCommandException as e:
            self.log.error(f"Error: {e}")
            return None

    def send_read_float_command(self, cmd: ReadCmd | ReadWriteCmd) -> float | None:
        """Send a read command to the laser and return the response as a float.
        :param cmd: The command to send.
        :type cmd: GenesisMXCmd.Read
        :return: The response from the laser as a float or None if an error occurred.
        :rtype: float | None
        """
        try:
            response = self.send_command(command=cmd.read())
            return float(response)
        except HOPSCommandException as e:
            self.log.error(f"Error: {e}")
            return None

    def send_read_int_command(self, cmd: ReadCmd | ReadWriteCmd) -> int | None:
        """Send a read command to the laser and return the response as an int.
        :param cmd: The command to send.
        :type cmd: GenesisMXCmd.Read
        :return: The response from the laser as an int or None if an error occurred.
        :rtype: int | None
        """
        try:
            response = self.send_command(command=cmd.read())
            return int(response)
        except HOPSCommandException as e:
            self.log.error(f"Error: {e}")
            return None
