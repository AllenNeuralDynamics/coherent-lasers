from coherent_lasers.genesis_mx.commands import ReadCmds, WriteCmds, OperationModes, Alarms
from coherent_lasers.common import HOPSDevice


class GenesisMX(HOPSDevice):
    def __init__(self, serial: str):
        super().__init__(serial)

    def send_read_command(self, cmd: ReadCmds):
        """Send a read command to the laser."""
        return self.send_command(cmd.value)

    def send_write_command(self, cmd: WriteCmds, value: float = None):
        """Send a write command to the laser."""
        if value is not None:
            self.send_command(f'{cmd.value}{value}')
        else:
            self.send_command(cmd.value)

    def enable(self):
        """Enable the laser."""
        if self.is_key_switch_closed:
            self.send_write_command(WriteCmds.SET_SOFTWARE_SWITCH, 1)
        else:
            raise ValueError(f'Key switch is not closed for laser {self.serial}')

    def disable(self):
        """Disable the laser."""
        self.send_write_command(WriteCmds.SET_SOFTWARE_SWITCH, 0)

    @property
    def mode(self):
        """Get the current mode of the laser: current mode or photomode."""
        mode_value = self.send_read_command(ReadCmds.CURRENT_MODE)
        return OperationModes(int(mode_value))

    @mode.setter
    def mode(self, value: OperationModes):
        """Set the mode of the laser."""
        self.send_write_command(WriteCmds.SET_MODE, value.value)

    @property
    def alarms(self):
        """Get the list of active alarms based on the fault code."""
        fault_code_value = int(self.send_read_command(ReadCmds.FAULT_CODE), 16)
        faults = Alarms.from_code(fault_code_value)
        return faults

    @property
    def power_mw(self):
        """Get the current power of the laser."""
        return float(self.send_read_command(ReadCmds.POWER))

    @power_mw.setter
    def power_mw(self, value: float):
        """Set the power of the laser."""
        self.send_write_command(WriteCmds.SET_POWER, value)

    @property
    def power_setpoint_mw(self):
        """Get the current power setpoint of the laser."""
        return float(self.send_read_command(ReadCmds.POWER_SETPOINT))

    @power_setpoint_mw.setter
    def power_setpoint_mw(self, value: float):
        """Set the power setpoint of the laser."""
        self.send_write_command(WriteCmds.SET_POWER, value)

    @property
    def ldd_current(self):
        """
        Get the LDD current of the laser.

        Measures the current supplied to the Laser Diode Driver (LDD).
        """
        return float(self.send_read_command(ReadCmds.LDD_CURRENT))

    @property
    def ldd_current_limit(self):
        """
        Get the LDD current limit of the laser.

        Measures the maximum current limit set for the Laser Diode Driver (LDD).
        """
        return float(self.send_read_command(ReadCmds.LDD_CURRENT_LIMIT))

    @property
    def temperature_c(self):
        """
        Get the main temperature of the laser.

        Description: Measures the temperature of the main thermoelectric cooler (TEC) that regulates the overall
        temperature of the laser head to ensure optimal performance and stability.
        """
        return float(self.send_read_command(ReadCmds.MAIN_TEMPERATURE))

    @property
    def shg_temperature_c(self):
        """
        Get the SHG temperature of the laser in degrees Celsius.

        Measures the temperature of the Second Harmonic Generation (SHG) heater. The SHG heater is crucial for
        maintaining the proper temperature for efficient frequency doubling processes that convert the laser light to
        the desired wavelength.
        """
        return float(self.send_read_command(ReadCmds.SHG_TEMPERATURE))

    @property
    def brf_temperature_c(self):
        """
        Get the BRF temperature of the laser in degrees Celsius.

        Measures the temperature of the Beam Reference Frequency (BRF) heater. The BRF heater is essential for
        maintaining the proper temperature for the frequency reference of the laser.
        """
        return float(self.send_read_command(ReadCmds.BRF_TEMPERATURE))

    @property
    def etalon_temperature_c(self):
        """
        Get the etalon temperature of the laser in degrees Celsius.

        Measures the temperature of the etalon heater. The etalon heater is crucial for maintaining the proper
        temperature for the etalon, which is used to stabilize the laser wavelength.
        """
        return float(self.send_read_command(ReadCmds.ETALON_TEMPERATURE))

    @property
    def main_tec_drive_v(self):
        """
        Get the main TEC drive voltage of the laser.

        Measures the drive voltage of the main thermoelectric cooler (TEC), which regulates the overall temperature of
        the laser head.
        """
        return float(self.send_read_command(ReadCmds.MAIN_TEC_DRIVE))

    @property
    def shg_heater_drive_v(self):
        """
        Get the SHG heater drive voltage of the laser.

        Measures the drive voltage of the Second Harmonic Generation (SHG) heater.
        """
        return float(self.send_read_command(ReadCmds.SHG_HEATER_DRIVE))

    @property
    def brf_heater_drive_v(self):
        """
        Get the BRF heater drive voltage of the laser.

        Measures the drive voltage of the Beam Reference Frequency (BRF) heater.
        """
        return float(self.send_read_command(ReadCmds.BRF_HEATER_DRIVE))

    @property
    def etalon_heater_drive_v(self):
        """
        Get the etalon heater drive voltage of the laser.

        Measures the drive voltage of the etalon heater.
        """
        return float(self.send_read_command(ReadCmds.ETALON_HEATER_DRIVE))

    @property
    def head(self):
        """Get the laser head information."""
        head_info = {}
        commands = {
            "serial": ReadCmds.HEAD_SERIAL,
            "type": ReadCmds.HEAD_TYPE,
            "hours": ReadCmds.HEAD_HOURS,
            "board_revision": ReadCmds.HEAD_BOARD_REVISION,
            "dio_status": ReadCmds.HEAD_DIO_STATUS
        }

        for key, command in commands.items():
            try:
                head_info[key] = self.send_read_command(command)
            except Exception as e:
                head_info[key] = f"Failed to read: {e}"

        return head_info

    @property
    def is_interlocked(self) -> bool:
        """
        Get the interlock status of the laser.

        Reads the status of the laser interlock (whether it is OK or not).
        """
        interlock_status = self.send_read_command(ReadCmds.INTERLOCK_STATUS)
        return interlock_status == 1

    @property
    def is_key_switch_closed(self) -> bool:
        """
        Get the key switch state of the laser.

        Reads the state of the key switch (on or off).
        """
        return self.send_read_command(ReadCmds.KEY_SWITCH_STATE) == 1

    @property
    def is_software_switch_closed(self) -> bool:
        """
        Get the software switch state of the laser.

        Reads the state of the software switch (enabled or disabled).
        """
        return self.send_read_command(ReadCmds.SOFTWARE_SWITCH_STATE) == 1

    @property
    def is_enabled(self) -> bool:
        """
        Check if the laser is enabled.
        """
        return self.is_interlocked and self.is_key_switch_closed and self.is_software_switch_closed

    @property
    def is_analog_input_enabled(self) -> bool:
        """
        Get the analog input status of the laser.

        Reads the status of the analog input (enabled or disabled).
        """
        state = self.send_read_command(ReadCmds.ANALOG_INPUT_STATUS)
        return state == 1

    @property
    def remote_control_enable(self) -> bool:
        """
        Get the remote control status of the laser.

        Reads whether remote control is enabled or disabled.
        """
        return self.send_read_command(ReadCmds.REMOTE_CONTROL_STATUS) == 1

    @remote_control_enable.setter
    def remote_control_enable(self, value: bool):
        """Set the remote control status of the laser."""
        self.send_write_command(WriteCmds.SET_REMOTE_CONTROL, 1 if value else 0)

    @property
    def is_ldd_enabled(self) -> bool:
        """
        Get the LDD enable state of the laser.

        Reads whether the Laser Diode Driver (LDD) is enabled or disabled.
        """
        return self.send_read_command(ReadCmds.LDD_ENABLE_STATE) == 1
