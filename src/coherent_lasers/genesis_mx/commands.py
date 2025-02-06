"""Coherent Genesis MX commands."""

from enum import Enum
from dataclasses import dataclass


class ReadCmds(Enum):
    """Genesis MX Read Commands"""

    CURRENT_MODE = "?CMODE"  # Read the current mode of the laser: 0 = Photo, 1 = Current
    FAULT_CODE = "?FF"  # Read the fault code of the laser
    POWER = "?P"  # Read the current power of the laser
    POWER_SETPOINT = "?PCMD"  # Read the power setpoint of the laser
    LDD_CURRENT = "?C"  # Read the current of the laser diode driver
    LDD_CURRENT_LIMIT = "?CLIM"  # Read the current limit of the laser diode driver

    # Temperature and Voltage Signals
    MAIN_TEMPERATURE = "?TMAIN"  # Read the main temperature of the laser
    SHG_TEMPERATURE = "?TSHG"
    BRF_TEMPERATURE = "?TBRF"
    ETALON_TEMPERATURE = "?TETA"
    MAIN_TEC_DRIVE = "?MAIND"
    SHG_HEATER_DRIVE = "?SHGD"
    BRF_HEATER_DRIVE = "?BRFD"
    ETALON_HEATER_DRIVE = "?ETAD"

    # Head Information
    HEAD_SERIAL = "?HID"
    HEAD_TYPE = "?HTYPE"
    HEAD_HOURS = "?HH"
    HEAD_DIO_STATUS = "?HEADDIO"
    HEAD_BOARD_REVISION = "?HBDREV"

    # Status Signals
    INTERLOCK_STATUS = "?INT"
    KEY_SWITCH_STATE = "?KSW"
    SOFTWARE_SWITCH_STATE = "?KSWCMD"
    ANALOG_INPUT_STATUS = "?ANA"
    LDD_ENABLE_STATE = "?L"
    REMOTE_CONTROL_STATUS = "?REM"

    PSDIO_STATUS = "?PSDIO"
    PSGLUE_INPUT_STATUS = "?PSGLUEIN"
    PSGLUE_OUTPUT_STATUS = "?PSGLUEOUT"


class WriteCmds(Enum):
    """Genesis MX Write Commands"""

    SET_POWER = "PCMD="
    SET_NONVOLATILE_POWER = "PMEM="
    SET_MODE = "CMODECMD="
    SET_ANALOG_INPUT = "ANACMD="
    SET_REMOTE_CONTROL = "REM="
    SET_SOFTWARE_SWITCH = "KSWCMD="


# Read/Write commands that can be read and written
# 1. Mode - Read: ?CMODE, Write: CMODECMD=
# 2. PowerSetpoint - Read: ?PCMD, Write: PCMD=
# 3. NonVolatilePower - Read: ?PMEM, Write: PMEM=
# 4. AnalogInput - Read: ?ANA, Write: ANACMD=
# 5. RemoteControl - Read: ?REM, Write: REM=
# 6. SoftwareSwitch - Read: ?KSWCMD, Write: KSWCMD=

# Read only commands
# Information commands (cache)
# 1. HeadSerial - Read: ?HID
# 2. HeadType - Read: ?HTYPE
# 3. HeadHours - Read: ?HH
# 4. HeadDioStatus - Read: ?HEADDIO
# 5. HeadBoardRevision - Read: ?HBDREV
# Signal commands
# 1. Power - Read: ?P
# 2. Current - Read: ?C
# 3. MainTemperature - Read: ?TMAIN
# 4. SHGTemperature - Read: ?TSHG
# 5. BRFTemperature - Read: ?TBRF
# 6. EtalonTemperature - Read: ?TETA
# 7. InterlockStatus - Read: ?INT
# 8. KeySwitchState - Read: ?KSW
# 9. FaultCode - Read: ?FF


@dataclass(frozen=True)
class ReadWrite:
    read_cmd: str
    write_cmd: str

    def read(self) -> str:
        return self.read_cmd

    def write(self, value) -> str:
        return f"{self.write_cmd}{value}"


class ReadWriteCmd(Enum):
    MODE = ReadWrite(read_cmd="?CMODE", write_cmd="CMODECMD=")
    POWER_SETPOINT = ReadWrite(read_cmd="?PCMD", write_cmd="PCMD=")
    NON_VOLATILE_POWER = ReadWrite(read_cmd="?PMEM", write_cmd="PMEM=")  # Not implemented
    ANALOG_INPUT = ReadWrite(read_cmd="?ANA", write_cmd="ANACMD=")
    REMOTE_CONTROL = ReadWrite(read_cmd="?REM", write_cmd="REM=")
    SOFTWARE_SWITCH = ReadWrite(read_cmd="?KSWCMD", write_cmd="KSWCMD=")

    def read(self) -> str:
        return self.value.read()

    def write(self, value: int | float) -> str:
        return self.value.write(value=value)


class ReadCmd(Enum):
    HEAD_SERIAL = "?HID"
    HEAD_TYPE = "?HTYPE"
    HEAD_HOURS = "?HH"
    HEAD_DIO_STATUS = "?HEADDIO"
    HEAD_BOARD_REVISION = "?HBDREV"
    # Signal Commands
    POWER = "?P"
    CURRENT = "?C"
    MAIN_TEMPERATURE = "?TMAIN"
    SHG_TEMPERATURE = "?TSHG"
    BRF_TEMPERATURE = "?TBRF"
    ETALON_TEMPERATURE = "?TETA"
    INTERLOCK_STATUS = "?INT"
    KEY_SWITCH_STATUS = "?KSW"
    FAULT_CODE = "?FF"

    def read(self) -> str:
        return self.value


class OperationMode(Enum):
    PHOTO = 0
    CURRENT = 1


class HeadType(Enum):
    MINIX = "MiniX"
    MINI00 = "Mini00"


class Alarm(Enum):
    NO_FAULT = (0x0000, "No fault")
    LASER_OVER_TEMPERATURE = (0x0001, "Laser over temperature")
    LASER_UNDER_TEMPERATURE = (0x0002, "Laser under temperature")
    OVER_CURRENT = (0x0003, "Over current")
    UNDER_CURRENT = (0x0004, "Under current")
    INTERLOCK_OPEN = (0x0005, "Interlock open")
    COOLANT_FLOW_LOW = (0x0006, "Coolant flow low")
    POWER_SUPPLY_FAILURE = (0x0007, "Power supply failure")
    LASER_DIODE_FAILURE = (0x0008, "Laser diode failure")
    TEC_FAILURE = (0x0009, "TEC failure")
    LASER_HEAD_OVER_TEMPERATURE = (0x000A, "Laser head over temperature")
    LASER_HEAD_UNDER_TEMPERATURE = (0x000B, "Laser head under temperature")
    SHG_HEATER_OVER_TEMPERATURE = (0x000C, "SHG heater over temperature")
    SHG_HEATER_UNDER_TEMPERATURE = (0x000D, "SHG heater under temperature")
    BRF_HEATER_OVER_TEMPERATURE = (0x000E, "BRF heater over temperature")
    BRF_HEATER_UNDER_TEMPERATURE = (0x000F, "BRF heater under temperature")
    ETALON_HEATER_OVER_TEMPERATURE = (0x0010, "Etalon heater over temperature")
    ETALON_HEATER_UNDER_TEMPERATURE = (0x0011, "Etalon heater under temperature")

    @classmethod
    def from_code(cls, code) -> list["Alarm"]:
        faults = []
        for fault in cls:
            if code & fault.value[0]:
                faults.append(fault)
        return faults if faults else [cls.NO_FAULT]
