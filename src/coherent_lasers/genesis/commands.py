from dataclasses import dataclass
from enum import Enum


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
