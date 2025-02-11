import time
from functools import cached_property

from .hops.cohrhops import CohrHOPSDevice, HOPSCommandException
from .base import GenesisMXInfo, LaserTemperature, LaserPower
from .commands import Alarm, OperationMode, ReadCmd, ReadWriteCmd


class GenesisMX(CohrHOPSDevice):
    serial2wavelength = {"A": 488, "J": 561, "R": 639}
    head_type2unit_factor = {"MiniX": 1000, "Mini00": 1}
    WARMUP_TIME = 5

    def __init__(self, serial: str) -> None:
        super().__init__(serial=serial)
        self.reset()

    @cached_property
    def info(self) -> GenesisMXInfo:
        """Get the laser's information.
        This includes the serial number, wavelength, head type, head hours, head DIO status, and head board revision.
        The information is cached for the lifetime of the object.
        :return: A GenesisMXInfo object containing the laser's information.
        :rtype: GenesisMXInfo
        """
        head_type = self.send_read_command(ReadCmd.HEAD_TYPE)
        return GenesisMXInfo(
            serial=self.serial,
            wavelength=self.serial2wavelength[self.serial[0]],
            head_type=head_type,
            head_hours=self.send_read_command(ReadCmd.HEAD_HOURS),
            head_dio_status=None,  # Unreliable command
            head_board_revision=self.send_read_command(ReadCmd.HEAD_BOARD_REVISION),
        )

    @cached_property
    def unit_factor(self) -> int:
        """Unit factor for the laser's power and power setpoint.
        Depending on the head_type, the power is returned in W or mW. We use mW as the standard unit.
        """
        if head_type := self.info.head_type:
            return self.head_type2unit_factor.get(head_type, 1)
        return 1

    @property
    def power(self) -> LaserPower:
        """Power and Power Setpoint in mW.
        :return: The power in mW or None if an error occurred.
        :rtype: LaserPower
        """
        value = self.send_read_float_command(ReadCmd.POWER)
        setpoint = self.send_read_float_command(ReadWriteCmd.POWER_SETPOINT)
        return LaserPower(
            value=value * self.unit_factor if value is not None else None,
            setpoint=setpoint * self.unit_factor if setpoint is not None else None,
        )

    @power.setter
    def power(self, power: float) -> None:
        """Set the power setpoint in mW.
        :param power: The power setpoint in mW.
        :type power: float
        """
        self.send_write_command(cmd=ReadWriteCmd.POWER_SETPOINT, value=power / self.unit_factor)

    @property
    def current(self) -> float | None:
        """Current in mA.
        :return: The current in mA or None if an error occurred.
        :rtype: float | None
        """
        return self.send_read_float_command(ReadCmd.CURRENT)

    @property
    def remote_control(self) -> bool | None:
        """Whether remote control is enabled.
        :return: True if enabled, False if disabled, None if an error occurred.
        :rtype: bool | None
        """
        if self.info.head_type == "MiniX":
            return self.send_read_bool_command(ReadWriteCmd.REMOTE_CONTROL)

    @remote_control.setter
    def remote_control(self, state: bool) -> None:
        if self.info.head_type != "MiniX":
            self.log.debug(f"Remote control not supported for head type: {self.info.head_type}")
        else:
            self.send_write_command(cmd=ReadWriteCmd.REMOTE_CONTROL, value=int(state))

    @property
    def key_switch(self) -> bool | None:
        """Key switch state.
        :return: True if enabled, False if disabled, None if an error occurred.
        :rtype: bool | None
        """
        return self.send_read_bool_command(ReadCmd.KEY_SWITCH_STATUS)

    @property
    def interlock(self) -> bool | None:
        """Interlock state.
        :return: True if enabled, False if disabled, None if an error occurred.
        :rtype: bool | None
        """
        return self.send_read_bool_command(ReadCmd.INTERLOCK_STATUS)

    @property
    def software_switch(self) -> bool | None:
        """Software switch state.
        :return: True if enabled, False if disabled, None if an error occurred.
        :rtype: bool | None
        """
        return self.send_read_bool_command(ReadWriteCmd.SOFTWARE_SWITCH)

    @software_switch.setter
    def software_switch(self, state: bool) -> None:
        if self.interlock:  # and self.key_switch:
            self.send_write_command(cmd=ReadWriteCmd.SOFTWARE_SWITCH, value=int(state))
        else:
            self.log.error(f"Cannot enable: interlock={self.interlock}, key_switch={self.key_switch}")

    @property
    def is_enabled(self) -> bool | None:
        """Whether the laser is enabled.
        :return: True if enabled, False if disabled, None if an error occurred.
        :rtype: bool | None
        """
        return self.interlock and self.key_switch and self.software_switch

    def enable(self) -> None:
        """Enable the laser. - turns on the software switch. Requires interlock and key switch to be enabled."""
        self.software_switch = True
        time.sleep(self.WARMUP_TIME)

    def disable(self) -> None:
        """Disable the laser. - turns off the software switch."""
        self.software_switch = False

    def close(self) -> None:
        """Disable the laser and close the connection."""
        self.disable()
        super().close()

    def reset(self) -> None:
        """Initialize the laser."""
        self.remote_control = True
        self.software_switch = False
        self.software_switch = True
        self.software_switch = False
        self.power = 0

    def await_power(self, max_wait_time: float = 15) -> None:
        """Wait for the laser to reach the power setpoint."""
        if not self.is_enabled:
            self.log.debug("Not awaiting power. Laser is not enabled.")
            return
        start_time = time.time()
        while True:
            power = self.power
            if power.value is not None and power.setpoint is not None and power.delta is not None:
                allowed_delta = max(power.setpoint * 0.15, 1.5)
                if abs(power.delta) <= allowed_delta:
                    break
            if time.time() - start_time > max_wait_time:
                self.log.debug(f"Power did not reach setpoint within {max_wait_time} seconds.")
                break
            time.sleep(0.25)

    @property
    def analog_input(self) -> bool | None:
        """Whether analog input control is enabled.
        :return: True if enabled, False if disabled, None if an error occurred.
        :rtype: bool | None
        """
        return self.send_read_bool_command(ReadWriteCmd.ANALOG_INPUT)

    @analog_input.setter
    def analog_input(self, state: bool) -> None:
        self.send_write_command(cmd=ReadWriteCmd.ANALOG_INPUT, value=int(state))

    @property
    def temperature(self) -> float | None:
        """Main temperature in °C.
        :return: The main temperature in °C or None if an error occurred."
        :rtype: float | None
        """
        return self.send_read_float_command(ReadCmd.MAIN_TEMPERATURE)

    def get_temperatures(self, include_only: list[str] | None = None) -> LaserTemperature:
        """Get the temperatures of the laser.

        :param exclude: List of temperature types to exclude from the result.
        :return: A GenesisMXTemperature object containing the temperatures.
        """
        temp_types = ["main", "shg", "brf", "etalon"]
        include = include_only or temp_types
        return LaserTemperature(
            main=self.send_read_float_command(ReadCmd.MAIN_TEMPERATURE) if "main" in include else None,
            shg=self.send_read_float_command(ReadCmd.SHG_TEMPERATURE) if "shg" in include else None,
            brf=self.send_read_float_command(ReadCmd.BRF_TEMPERATURE) if "brf" in include else None,
            etalon=None,  # Command didn't work for MiniX and Mini00
        )

    @property
    def mode(self) -> OperationMode | None:
        """Supports CURRENT and PHOTO modes.
        :return: The current operation mode or None if an error occurred.
        :rtype: OperationMode | None
        """
        if mode := self.send_read_int_command(ReadWriteCmd.MODE) is not None:
            return OperationMode(mode)

    @mode.setter
    def mode(self, mode: OperationMode) -> None:
        self.send_write_command(cmd=ReadWriteCmd.MODE, value=mode.value)

    @property
    def alarms(self) -> list[str] | None:
        """Retrieve active alarms as a list of descriptive strings."""
        res = self.send_read_command(ReadCmd.FAULT_CODE)
        return Alarm.parse(int(res, 16)) if res is not None else None

    def __repr__(self) -> str:
        return f"GenesisMX(serial={self.serial}, wavelength={self.info.wavelength}, head_type={self.info.head_type})"

    # send commands helper functions
    def send_write_command(self, cmd: ReadWriteCmd, value: float | int, wait: float = 0.0) -> float | None:
        """
        Sends a write command, then reads back the new value from the laser.

        :param cmd: The read/write command to send.
        :param value: The value to send with the command.
        :return: The newly-updated value from the laser if successful, None otherwise.
        """
        try:
            # 1. Write the new value
            self.send_command(command=cmd.write(value))

            time.sleep(wait) if wait else None

            # 2. Read back the updated value
            if response_str := self.send_command(command=cmd.read()):
                # 3. Attempt to parse the response as a float
                new_value = float(response_str)

                if new_value != value:
                    self.log.debug(f"Write/readback mismatch: {value} != {new_value}")

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
            self.log.error(e)
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
            if response is not None:
                response = int(response.strip())
            return bool(response)
        except HOPSCommandException as e:
            self.log.error(e)
            return None

    def send_read_float_command(self, cmd: ReadCmd | ReadWriteCmd) -> float | None:
        """Send a read command to the laser and return the response as a float.
        :param cmd: The command to send.
        :type cmd: GenesisMXCmd.Read
        :return: The response from the laser as a float or None if an error occurred.
        :rtype: float | None
        """
        try:
            if response := self.send_command(command=cmd.read()):
                return float(response)
        except HOPSCommandException as e:
            self.log.error(e)
            return None

    def send_read_int_command(self, cmd: ReadCmd | ReadWriteCmd) -> int | None:
        """Send a read command to the laser and return the response as an int.
        :param cmd: The command to send.
        :type cmd: GenesisMXCmd.Read
        :return: The response from the laser as an int or None if an error occurred.
        :rtype: int | None
        """
        try:
            if response := self.send_command(command=cmd.read()):
                return int(response)
        except HOPSCommandException as e:
            self.log.error(e)
            return None
