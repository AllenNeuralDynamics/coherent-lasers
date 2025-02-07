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
    MAIN_TEC_ERROR = (0x0008, "Main TEC error")
    LBO_BRF_TEMP_ERROR = (0x0010, "LBO or BRF temperature not OK")
    INTERLOCK_FAULT = (0x0020, "Interlock fault")
    SHUTTER_ERROR = (0x0100, "Shutter error")
    GLUE_BOARD_ERROR = (0x0200, "Glue board error")
    LDD_CURRENT_LIMIT = (0x0800, "LDD at current limit")

    @classmethod
    def parse(cls, code: int) -> list[str]:
        """Extract active alarm messages from a fault code."""
        return [fault.value[1] for fault in cls if fault.value[0] & code] or [cls.NO_FAULT.value[1]]
