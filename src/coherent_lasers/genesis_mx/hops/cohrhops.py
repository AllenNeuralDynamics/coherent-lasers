import asyncio
import ctypes as C
from ctypes.util import find_library
from enum import IntEnum
from functools import cached_property
import logging
import os
import threading
from threading import RLock
import time

# Make sure prerequisites are met ######################################################################################
DLL_DIR = os.path.dirname(os.path.abspath(__file__))
HOPS_DLL = os.path.join(DLL_DIR, "CohrHOPS.dll")
REQUIRED_DLLS = ["CohrHOPS", "CohrFTCI2C"]

# Validate the system is Windows and 64-bit
if not (os.name == "nt" and os.environ["PROCESSOR_ARCHITECTURE"].endswith("64")):
    raise OSError("This package only supports 64-bit Windows systems.")

# Validate the required DLLs are present
os.environ["PATH"] = DLL_DIR + os.pathsep + os.environ["PATH"]

for dll_name in REQUIRED_DLLS:
    dll_path = find_library(dll_name)
    if dll_path is None:
        raise FileNotFoundError(f"Required 64-bit DLL file not found: {dll_name}.dll")
try:
    C.CDLL(find_library("CohrHOPS"))
    C.CDLL(find_library("CohrFTCI2C"))
except Exception as e:
    print(f"Error loading DLLs: {e}")
    raise

########################################################################################################################

# Constants
MAX_DEVICES = 20
MAX_STRLEN = 100
# HOPSResponse.OK = 0


class HOPSResponse(IntEnum):
    OK = 0
    INVALID_HANDLE = -1
    INVALID_HEAD = -2
    INVALID_COMMAND = -3
    INVALID_DATA = -4
    I2C_ERROR = -5
    USB_ERROR = -6
    FTCI2C_DLL_FILE_NOT_FOUND = -100
    FTCI2C_DLL_FUNCTION_NOT_FOUND = -101
    FTCI2C_DLL_EXCEPTION = -102
    NXP_ERROR = -200
    RS232_ERROR = -300
    THREAD_ERROR = -400
    OTHER_ERROR = -999

    def string(self) -> str:
        return self.name.replace("_", " ").title()


CRITICAL_ERRORS = [
    HOPSResponse.FTCI2C_DLL_FILE_NOT_FOUND,
    HOPSResponse.FTCI2C_DLL_FUNCTION_NOT_FOUND,
    HOPSResponse.FTCI2C_DLL_EXCEPTION,
    HOPSResponse.NXP_ERROR,
    HOPSResponse.RS232_ERROR,
    HOPSResponse.I2C_ERROR,
    HOPSResponse.USB_ERROR,
    HOPSResponse.THREAD_ERROR,
    HOPSResponse.OTHER_ERROR,
]


# Exceptions
class HOPSException(Exception):
    def __init__(self, message, code: HOPSResponse | None = None) -> None:
        if code is not None:
            message = f"{message} - [{HOPSResponse(code).name}]"
        super().__init__(message)


# Exception for when a message is sent and an error is returned
class HOPSCommandException(HOPSException):
    def __init__(self, command: str, code: HOPSResponse) -> None:
        super().__init__(f"Error sending: {command}", code)


# C types
LPULPTR = C.POINTER(C.c_ulonglong)
COHRHOPS_HANDLE = C.c_ulonglong
LPDWORD = C.POINTER(C.c_ulong)
LPSTR = C.c_char_p


# Data structures
class HandleCollection:
    def __init__(self) -> None:
        self._ptr = (COHRHOPS_HANDLE * MAX_DEVICES)()
        self._len = C.c_ulong()

    def __getitem__(self, index):
        return self._ptr[index]

    def pointer(self) -> C.Array[C.c_ulonglong]:
        return self._ptr

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    @property
    def handles(self) -> list[str]:
        return [hex(int(h)) for h in self][: len(self)]

    def len_pointer(self):
        return C.byref(self._len)

    def __len__(self):
        return self._len.value

    def __str__(self):
        return f"{len(self)} HOPSHandles({[hex(h) for h in self]})"


class CohrHOPSManager:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self._lock = RLock()
        self._dll = C.CDLL(HOPS_DLL)
        self._wrap_dll_functions()
        self._connections: HandleCollection = HandleCollection()
        self._removed_connections: HandleCollection = HandleCollection()
        self._added_connections: HandleCollection = HandleCollection()
        self._serials: dict[str, COHRHOPS_HANDLE] = {}
        self._closed_serials: set[str] = set()

    def discover(self) -> list[str]:
        """Discover connected devices and return a list of serial numbers."""
        with self._lock:
            # Fetch device handles
            res = self._check_for_devices(
                self._connections.pointer(),
                self._connections.len_pointer(),
                self._added_connections.pointer(),
                self._added_connections.len_pointer(),
                self._removed_connections.pointer(),
                self._removed_connections.len_pointer(),
            )
            if res != HOPSResponse.OK:
                self.log.warning(f"Error checking for devices: {HOPSResponse(res).name}")
            if len(self._connections) == 0:
                raise HOPSException("No devices found.")

            # initialize devices and get serials
            self.serials.clear()
            response = C.create_string_buffer(MAX_STRLEN)

            uninitialized_handles = []
            failed_serials = []
            for handle in self._connections:
                res = self._initialize_handle(handle, response)
                if res != HOPSResponse.OK:
                    self.log.error(f"Initialization failed for handle {hex(int(handle))}, error: {res}")
                    self._close(handle)
                    uninitialized_handles.append(hex(int(handle)))
                    continue
                res = self._send_command(handle, "?HID".encode("utf-8"), response)
                if res != HOPSResponse.OK:
                    self.log.error(f"Error getting serial number for handle {hex(int(handle))}, error: {res}")
                    self._close(handle)
                    failed_serials.append(hex(int(handle)))
                    continue
                serial = response.value.decode("utf-8").strip()
                self._serials[serial] = handle
            if uninitialized_handles:
                self.log.warning(f"Failed to initialize handles: {uninitialized_handles}")
                raise HOPSException(f"Error initializing handles: {uninitialized_handles}")
            if failed_serials:
                self.log.warning(f"Failed to get serial numbers for handles: {failed_serials}")
                raise HOPSException(f"Error getting serial numbers for handles: {failed_serials}")

            return list(self._serials.keys())

    def send_command(self, serial: str, command: str) -> str:
        """Send a command to the device with the given serial number.
        If the device is not found, it will attempt to rediscover devices.
        :param serial: The serial number of the device.
        :param command: The command to send.
        :type serial: str
        :type command: str
        :return: The response from the device.
        :rtype: str
        :raises HOPSCommandException: If the command fails.
        """
        response = C.create_string_buffer(MAX_STRLEN)

        def send_cohrhops_command(handle: COHRHOPS_HANDLE, command: str):
            res = self._send_command(handle, command.encode("utf-8"), response)
            return res

        def decode_response(response):
            return response.value.decode("utf-8").strip()

        # Check if device is known; if not, run discovery.
        if serial not in self.serials:
            self.log.warning(f"Device {serial} not found; rediscovering...")
            self.discover()

        if serial not in self.serials:
            raise HOPSException(message=f"Unable to send command: {command} to serial: {serial}. Device not found")

        with self._lock:
            # Try to send the command
            res = send_cohrhops_command(self._serials[serial], command)

            if res in CRITICAL_ERRORS:
                self.log.critical(f"Error sending command: {command}")
                raise HOPSCommandException(command, res)

            if res == HOPSResponse.INVALID_COMMAND | HOPSResponse.INVALID_DATA:
                raise HOPSCommandException(command, res)

            if res == HOPSResponse.OK:
                return decode_response(response)

            # if we get to this point it means the res was one of: INVALID_HANDLE, INVALID_HEAD
            self.discover()

            res = send_cohrhops_command(self._serials[serial], command)

            if res == HOPSResponse.INVALID_COMMAND | HOPSResponse.INVALID_DATA:
                raise HOPSCommandException(command=command, code=res)

            if res == HOPSResponse.OK:
                return decode_response(response)

            self.log.critical(f"Error sending command: {command}")
            raise HOPSCommandException(command=command, code=res)

    async def async_send_command(self, serial: str, command: str) -> str:
        """Asynchronously sends a command by offloading the blocking call to a thread in the default executor.
        :param serial: The serial number of the device.
        :param command: The command to send.
        :type serial: str
        :type command: str
        :return: The response from the device.
        :rtype: str
        :raises HOPSCommandException: If the command fails.
        """
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, self.send_command, serial, command)
        return response

    def close_device(self, serial: str) -> None:
        self._closed_serials.add(serial)

    def close(self):
        self.log.debug(f"Closing hops manager. {len(self._connections)} handles to close.")
        with self._lock:
            for handle in self._connections:
                self._close(handle)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def serials(self) -> list[str]:
        return list(self._serials.keys())

    @cached_property
    def version(self) -> str:
        buffer = C.create_string_buffer(MAX_STRLEN)
        res = self._get_dll_version(buffer)
        if res != HOPSResponse.OK:
            raise Exception(f"Error getting DLL version: {res}")
        return buffer.value.decode("utf-8")

    def _refresh_connected_handles(self):
        with self._lock:
            res = self._check_for_devices(
                self._connections.pointer(),
                self._connections.len_pointer(),
                self._added_connections.pointer(),
                self._added_connections.len_pointer(),
                self._removed_connections.pointer(),
                self._removed_connections.len_pointer(),
            )
            if res != HOPSResponse.OK:
                raise HOPSException(f"Error checking for devices: {res}")
            self.log.debug(f"Updated Handles: {self._connections.handles}")

    def _initialize_device(self, handle: COHRHOPS_HANDLE) -> bool:
        """Attempt to initialize the device. If initialization fails, try cleanup and return False."""
        with self._lock:
            self.log.debug(f"Initializing device {hex(int(handle))}")
            headtype = C.create_string_buffer(MAX_STRLEN)
            res = self._initialize_handle(handle, headtype)
            if res != HOPSResponse.OK:
                self.log.error(f"Initialization failed for handle {hex(int(handle))}, error: {res}")
                # Attempt to close the handle to free resources.
                self._close(handle)
                return False
            self.log.debug(
                f"Initialization succeeded for handle {hex(int(handle))}, head type: {headtype.value.decode('utf-8')}"
            )
            return True

    def _refresh_serials(self):
        def query_serial(handle: COHRHOPS_HANDLE) -> str | None:
            response = C.create_string_buffer(MAX_STRLEN)
            res = self._send_command(handle, "?HID".encode("utf-8"), response)
            return response.value.decode("utf-8").strip() if res == HOPSResponse.OK else None

        # with self._lock:
        self.log.debug(f"Getting serials for {len(self._connections)} handles.")
        fails = []
        for handle in self._connections:
            if serial := query_serial(handle) or (self._initialize_device(handle) and (serial := query_serial(handle))):
                self._serials[serial] = handle
            else:
                fails.append(handle)

        if fails:
            self.log.warning(f"Failed to get serials for handles: {fails}")
            raise HOPSException(f"Error getting serial numbers for handles: {fails}")

    def _wrap_dll_functions(self):
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


_cohrhops_manager_instance = None
_cohrhops_manager_lock = threading.Lock()


def get_cohrhops_manager() -> CohrHOPSManager:
    global _cohrhops_manager_instance
    if _cohrhops_manager_instance is None:
        with _cohrhops_manager_lock:
            if _cohrhops_manager_instance is None:
                _cohrhops_manager_instance = CohrHOPSManager()
                attempts = 3
                timeout = 5
                for attempt in range(attempts):
                    try:
                        _cohrhops_manager_instance.discover()
                        break
                    except HOPSException:
                        msg = f"Error discovering devices: Attempt {attempt + 1} of {attempts}."
                        msg += f" Retrying in {timeout} seconds ..." if attempt < attempts - 1 else ""
                        _cohrhops_manager_instance.log.debug(msg)
                        if attempt < attempts - 1:
                            time.sleep(timeout)
    return _cohrhops_manager_instance


class CohrHOPSDevice:
    _manager = get_cohrhops_manager()

    def __init__(self, serial: str):
        self.serial = serial
        self.log = logging.getLogger(f"{__name__}.{serial}")

    def send_command(self, command: str) -> str | None:
        """Send a command to the device.
        :param command: The command to send.
        :type command: str
        :return: The response from the device.
        :rtype: str
        :raises HOPSCommandException: If the command fails.
        """
        return self._manager.send_command(self.serial, command)

    async def async_send_command(self, command: str) -> str | None:
        """Anynchronously send a command to the device.
        :param command: The command to send.
        :type command: str
        :return: The response from the device.
        :rtype: str
        :raises HOPSCommandException: If the command fails.
        """
        return await self._manager.async_send_command(self.serial, command)

    def close(self):
        self._manager.close_device(self.serial)
