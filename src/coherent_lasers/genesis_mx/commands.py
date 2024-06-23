"""Coherent Genesis MX commands."""
from enum import Enum


class ReadCmds(Enum):
    """Genesis MX Read Commands"""
    CURRENT_MODE = "?CMODE"         # Read the current mode of the laser: 0 = Photo, 1 = Current
    FAULT_CODE = "?FF"              # Read the fault code of the laser
    POWER = "?P"                    # Read the current power of the laser
    POWER_SETPOINT = "?PCMD"        # Read the power setpoint of the laser
    LDD_CURRENT = "?C"              # Read the current of the laser diode driver
    LDD_CURRENT_LIMIT = "?CLIM"     # Read the current limit of the laser diode driver

    # Temperature and Voltage Signals
    MAIN_TEMPERATURE = "?TMAIN"     # Read the main temperature of the laser
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


class OperationModes(Enum):
    PHOTO = 0
    CURRENT = 1


class Alarms(Enum):
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
    def from_code(cls, code):
        faults = []
        for fault in cls:
            if code & fault.value[0]:
                faults.append(fault)
        return faults if faults else [cls.NO_FAULT]
