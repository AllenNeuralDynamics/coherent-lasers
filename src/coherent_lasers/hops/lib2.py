import asyncio
import ctypes as C
from ctypes.util import find_library
from functools import cached_property
import logging
import os
import threading
from threading import Lock
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
COHRHOPS_OK = 0
MAX_DEVICES = 20
MAX_STRLEN = 100


# Exceptions
class HOPSException(Exception):
    def __init__(self, message, code: int | None = None) -> None:
        if code is not None:
            message = f"{message} (Error code: {code})"
        super().__init__(message)


# Exception for when a message is sent and an error is returned
class HOPSCommandException(HOPSException):
    def __init__(self, message, command: str, code: int) -> None:
        super().__init__(message, code)
        message = f"Error [{code}] sending command: {command}. {message}"
        super().__init__(message)


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

    @property
    def handles(self) -> list[COHRHOPS_HANDLE]:
        return [self[i] for i in range(len(self))]

    def len_pointer(self):
        return C.byref(self._len)

    def __len__(self):
        return self._len.value

    def __str__(self):
        return f"{len(self)} HOPSHandles({[hex(h) for h in self]})"


class CohrHOPSManager:
    def __init__(self, refresh_interval: float = 5):
        self._log = logging.getLogger(__name__)
        self._lock = Lock()
        self._dll = C.CDLL(HOPS_DLL)
        self._wrap_dll_functions()
        self._connections: HandleCollection = HandleCollection()
        self._removed_connections: HandleCollection = HandleCollection()
        self._added_connections: HandleCollection = HandleCollection()
        self._serials: dict[str, COHRHOPS_HANDLE] = {}
        self._refresh_interval = refresh_interval
        self.close()
        self.discover()
        # self._discover_thread = threading.Thread(target=self._discover_loop, daemon=True)
        # self._discover_thread.start()

    def discover(self) -> list[str]:
        max_attempts = 5
        timeout = 1
        attempts = 0

        while attempts < max_attempts:
            self._refresh_connected_handles()
            if len(self._connections) > 0:
                break
            self._log.warning(
                f"No devices found, attempt {attempts + 1}/{max_attempts}. Retrying in {timeout} seconds..."
            )
            time.sleep(timeout)
            attempts += 1

        if len(self._connections) == 0:
            self._log.error(f"No devices found after {max_attempts} attempts.")
            raise HOPSException(f"No devices found after {max_attempts} attempts.")

        self._refresh_serials()
        return self.serials

    def _discover_loop(self):
        while True:
            self.discover()
            time.sleep(self._refresh_interval)

    def send_command(self, serial: str, command: str) -> str:
        def send_cohrhops_command(handle: COHRHOPS_HANDLE, command: str) -> str | None:
            response = C.create_string_buffer(MAX_STRLEN)
            res = self._send_command(handle, command.encode("utf-8"), response)
            return response.value.decode("utf-8").strip() if res == COHRHOPS_OK else None

        if serial not in self.serials:
            self._log.warning(f"Device {serial} not found. Attempting to discover devices...")
            self.discover()

        if serial not in self.serials:
            raise HOPSCommandException("Device not found", command, -404)

        with self._lock:
            if response := send_cohrhops_command(self._serials[serial], command):
                return response
            if self._initialize_device(self._serials[serial]):
                response = send_cohrhops_command(self._serials[serial], command)
                if response:
                    return response
            raise HOPSCommandException("Error sending command", command, -500)

    async def async_send_command(self, serial: str, command: str) -> str:
        """
        Asynchronously sends a command by offloading the blocking call
        to a thread in the default executor.
        """
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, self.send_command, serial, command)
        return response

    def close_device(self, serial: str) -> None:
        with self._lock:
            handle = self._serials.get(serial)
            if not handle:
                self._log.warning(f"Unable to close {serial}. Device not found.")
                return
            res = self._close(handle)
            if res != COHRHOPS_OK:
                self._log.error(f"Error closing device - {serial}.")

    def close(self):
        with self._lock:
            for handle in self._connections:
                self._close(handle)

    def __del__(self):
        self.close()

    @property
    def serials(self) -> list[str]:
        return list(self._serials.keys())

    @cached_property
    def version(self) -> str:
        buffer = C.create_string_buffer(MAX_STRLEN)
        res = self._get_dll_version(buffer)
        if res != COHRHOPS_OK:
            raise Exception(f"Error getting DLL version: {res}")
        return buffer.value.decode("utf-8")

    def _refresh_connected_handles(self):
        res = self._check_for_devices(
            self._connections.pointer(),
            self._connections.len_pointer(),
            self._added_connections.pointer(),
            self._added_connections.len_pointer(),
            self._removed_connections.pointer(),
            self._removed_connections.len_pointer(),
        )
        if res != COHRHOPS_OK:
            raise HOPSException(f"Error checking for devices: {res}")
        self._log.debug(f"Updated conection info. Handles: {self._connections.handles}")

    def _initialize_device(self, handle: COHRHOPS_HANDLE) -> bool:
        headtype = C.create_string_buffer(MAX_STRLEN)
        res = self._initialize_handle(handle, headtype)
        return res == COHRHOPS_OK

    def _refresh_serials(self):
        def query_serial(handle: COHRHOPS_HANDLE) -> str | None:
            response = C.create_string_buffer(MAX_STRLEN)
            res = self._send_command(handle, "?HID".encode("utf-8"), response)
            return response.value.decode("utf-8").strip() if res == COHRHOPS_OK else None

        with self._lock:
            fails = []
            for i in range(len(self._connections)):
                handle = self._connections[i]
                if serial := query_serial(handle) or (
                    self._initialize_device(handle) and (serial := query_serial(handle))
                ):
                    self._serials[serial] = handle
                else:
                    fails.append(handle)

            if fails:
                self._log.warning(f"Failed to get serials for handles: {fails}")
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
    return _cohrhops_manager_instance


class CohrHOPSDevice:
    _manager = get_cohrhops_manager()

    def __init__(self, serial: str):
        self.serial = serial

    def send_command(self, command: str) -> str:
        return self._manager.send_command(self.serial, command)

    async def async_send_command(self, command: str) -> str:
        return await self._manager.async_send_command(self.serial, command)

    def close(self):
        self._manager.close_device(self.serial)


if __name__ == "__main__":
    TEST_COMMAND = "?HID"

    def sync_example():
        # Get the manager instance (this automatically performs discovery)
        manager = get_cohrhops_manager()

        # manager.discover()

        # Print the DLL version
        print("DLL Version:", manager.version)

        # List discovered device serials
        serials = manager.serials
        print("Discovered Devices:", serials)

        if not serials:
            print("No devices discovered.")
            return

        for serial in serials:
            try:
                response = manager.send_command(serial, TEST_COMMAND)
                print(f"Synchronous response from device {serial}: {response}")
            except HOPSCommandException as e:
                print(f"Synchronous command failed: {e}")

    async def async_example():
        manager = get_cohrhops_manager()

        # Print the DLL version
        print("DLL Version:", manager.version)

        # List discovered device serials
        serials = manager.serials
        print("Discovered Devices:", serials)

        if not serials:
            print("No devices discovered.")
            return

        for serial in serials:
            try:
                response = await manager.async_send_command(serial, TEST_COMMAND)
                print(f"Asynchronous response from device {serial}: {response}")
            except HOPSCommandException as e:
                print(f"Asynchronous command failed: {e}")

    logging.basicConfig(level=logging.INFO)

    print("=== Synchronous Example ===")
    sync_example()

    print("\n=== Asynchronous Example ===")
    asyncio.run(async_example())
