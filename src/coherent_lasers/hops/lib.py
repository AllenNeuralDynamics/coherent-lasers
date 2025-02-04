import ctypes as C
from ctypes.util import find_library
import logging
import os
import threading

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

DLL_DIR = os.path.dirname(os.path.abspath(__file__))

# Add the DLL directory to the DLL search path
# os.add_dll_directory(DLL_DIR)

# Add the DLL directory to the system PATH
os.environ["PATH"] = DLL_DIR + os.pathsep + os.environ["PATH"]

# Check for required DLLs using ctypes.util.find_library
REQUIRED_DLLS = ["CohrHOPS", "CohrFTCI2C"]
for dll_name in REQUIRED_DLLS:
    dll_path = find_library(dll_name)
    if dll_path is None:
        raise FileNotFoundError(f"Required 64-bit DLL file not found: {dll_name}.dll")

# Try to load the DLLs to ensure they're accessible
try:
    C.CDLL(find_library("CohrHOPS"))
    C.CDLL(find_library("CohrFTCI2C"))
except Exception as e:
    logger.error(f"Error loading 64-bit DLLs: {e}")
    raise


# Constants
HOPS_DLL = os.path.join(DLL_DIR, "CohrHOPS.dll")
MAX_DEVICES = 20
MAX_STRLEN = 100
COHRHOPS_OK = 0

# C types
LPULPTR = C.POINTER(C.c_ulonglong)
COHRHOPS_HANDLE = C.c_ulonglong
LPDWORD = C.POINTER(C.c_ulong)
LPSTR = C.c_char_p


class HOPSException(Exception):
    def __init__(self, message, code: int | None = None) -> None:
        if code is not None:
            message = f"{message} (Error code: {code})"
        super().__init__(message)


class HOPSDevicesList:
    def __init__(self):
        self.devices = (COHRHOPS_HANDLE * MAX_DEVICES)()

    def __getitem__(self, index):
        return self.devices[index]

    def pointer(self):
        return self.devices


class HOPSManager:
    def __init__(self):
        self._log = logging.getLogger(__name__)

        self._handles: dict[COHRHOPS_HANDLE, str] = {}
        self._active_serials: set[str] = set()

        self._dll = C.CDLL(HOPS_DLL)
        self._wrap_functions()

        self._devices_connected = HOPSDevicesList()
        self._number_of_devices_connected = C.c_ulong()
        self._devices_added = HOPSDevicesList()
        self._number_of_devices_added = C.c_ulong()
        self._devices_removed = HOPSDevicesList()
        self._number_of_devices_removed = C.c_ulong()

        self._fetch_device_connection_info()
        self._activate_all_devices()

    def initialize_device(self, serial: str) -> COHRHOPS_HANDLE:
        self._active_serials.add(serial)
        self._refresh_devices()
        return next(handle for handle, ser in self._handles.items() if ser == serial)

    def close_device(self, serial: str) -> None:
        self._active_serials.remove(serial)
        self._refresh_devices()

    def send_device_command(self, serial: str, command: str) -> str:
        handle = next(handle for handle, ser in self._handles.items() if ser == serial)
        response: C.Array[C.c_char] = C.create_string_buffer(MAX_STRLEN)
        res = self._send_command(handle, command.encode(), response)
        if res != COHRHOPS_OK:
            raise HOPSException(f"Error sending command to device {serial}", res)
        return response.value.decode("utf-8").strip()

    @property
    def version(self) -> str:
        buffer = C.create_string_buffer(MAX_STRLEN)
        res = self._get_dll_version(buffer)
        if res == COHRHOPS_OK:
            return buffer.value.decode("utf-8")
        else:
            raise Exception(f"Error getting DLL version: {res}")

    # def __del__(self) -> None:
    #     self._fetch_device_connection_info()
    #     for i in range(self._number_of_devices_connected.value):
    #         handle = self._devices_connected[i]
    #         self._close(handle)

    def _wrap_functions(self):
        self._initialize_handle = self._dll.CohrHOPS_InitializeHandle
        self._initialize_handle.argtypes = [COHRHOPS_HANDLE, LPSTR]
        self._initialize_handle.restype = int

        self._send_command = self._dll.CohrHOPS_SendCommand
        self._send_command.argtypes = [COHRHOPS_HANDLE, LPSTR, LPSTR]
        self._send_command.restype = int

        self._close = self._dll.CohrHOPS_Close
        self._close.argtypes = [COHRHOPS_HANDLE]
        self._close.restype = int

        self._get_dll_version = self._dll.CohrHOPS_GetDLLVersion
        self._get_dll_version.argtypes = [LPSTR]
        self._get_dll_version.restype = int

        self._check_for_devices = self._dll.CohrHOPS_CheckForDevices
        self._check_for_devices.argtypes = [
            LPULPTR,
            LPDWORD,
            LPULPTR,
            LPDWORD,
            LPULPTR,
            LPDWORD,
        ]
        self._check_for_devices.restype = int

    def _fetch_device_connection_info(self):
        self._log.debug("Updating devices info...")
        res = self._check_for_devices(
            self._devices_connected.pointer(),
            C.byref(self._number_of_devices_connected),
            self._devices_added.pointer(),
            C.byref(self._number_of_devices_added),
            self._devices_removed.pointer(),
            C.byref(self._number_of_devices_removed),
        )
        if res != COHRHOPS_OK:
            raise HOPSException(f"Error checking for devices: {res}")
        self._log.debug(
            f"Updated devices info. Connected: {self._number_of_devices_connected.value}"
        )

    def _activate_all_devices(self):
        self._log.debug("Activating all devices...")
        connected_handles = {
            self._devices_connected[i]
            for i in range(self._number_of_devices_connected.value)
        }
        for handle in connected_handles:
            self._initialize_device_by_handle(handle)
            ser = self._get_device_serial(handle)
            self._handles[handle] = ser
            self._active_serials.add(ser)
        self._log.debug("Registered Handles: " + str(self._handles))
        self._log.debug("Active Devices: " + str(self._active_serials))

    def _validate_active_devices(self):
        self._log.debug("Validating active devices...")
        connected_handles = {
            self._devices_connected[i]
            for i in range(self._number_of_devices_connected.value)
        }
        for handle in connected_handles:
            self._initialize_device_by_handle(handle)
            ser = self._get_device_serial(handle)
            self._handles[handle] = ser
            if ser not in self._active_serials:
                self._close_device_by_handle(handle)
        self._handles = {
            handle: ser
            for handle, ser in self._handles.items()
            if ser in self._active_serials
        }
        self._log.debug("Registered Handles: " + str(self._handles))
        self._log.debug("Active Devices: " + str(self._active_serials))

    def _refresh_devices(self):
        self._fetch_device_connection_info()
        self._validate_active_devices()

    def _get_device_serial(self, handle: COHRHOPS_HANDLE) -> str:
        response = C.create_string_buffer(MAX_STRLEN)
        res = self._send_command(handle, "?HID".encode("utf-8"), response)
        if res != COHRHOPS_OK:
            raise HOPSException(f"Error getting serial number for handle {handle}")
        return response.value.decode("utf-8").strip()

    def _initialize_device_by_handle(self, handle: COHRHOPS_HANDLE) -> None:
        """Given a handle, initialize the device and return the serial number."""
        headtype = C.create_string_buffer(MAX_STRLEN)
        res = self._initialize_handle(handle, headtype)
        if res != COHRHOPS_OK:
            raise HOPSException("Error initializing device")

    def _close_device_by_handle(self, handle: COHRHOPS_HANDLE) -> None:
        """Close the device associated with the given handle."""
        res = self._close(handle)
        if res != COHRHOPS_OK:
            raise HOPSException(f"Error closing device with handle {handle}")


_hops_manager_instance = None
_hops_manager_lock = threading.Lock()


def get_hops_manager():
    global _hops_manager_instance
    if _hops_manager_instance is None:
        with _hops_manager_lock:
            if _hops_manager_instance is None:
                _hops_manager_instance = HOPSManager()
    return _hops_manager_instance


class HOPSDevice:
    _manager = get_hops_manager()

    def __init__(self, serial: str):
        self.serial = serial

    def send_command(self, command: str) -> str:
        return self._manager.send_device_command(self.serial, command)

    def close(self):
        self._manager.close_device(self.serial)
