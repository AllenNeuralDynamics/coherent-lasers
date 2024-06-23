import ctypes as C
import os
from typing import Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
DLL_DIR = os.path.join(current_dir, "dll")

HOPS_DLL = os.path.join(DLL_DIR, "CohrHOPS.dll")

MAX_DEVICES = 20
MAX_STRLEN = 100

COHRHOPS_OK = 0
COHRHOPS_INVALID_COMMAND = -3

LPULPTR = C.POINTER(C.c_ulonglong)
COHRHOPS_HANDLE = C.c_ulonglong
LPDWORD = C.POINTER(C.c_ulong)
LPSTR = C.c_char_p
INT32 = C.c_int32


class HOPSDLLWrapper:
    def __init__(self, dll_path):
        self.dll = C.CDLL(dll_path)
        self._wrap_functions()

    def _wrap_functions(self):
        self.initialize_handle = self.dll.CohrHOPS_InitializeHandle
        self.initialize_handle.argtypes = [COHRHOPS_HANDLE, LPSTR]
        self.initialize_handle.restype = int

        self.send_command = self.dll.CohrHOPS_SendCommand
        self.send_command.argtypes = [COHRHOPS_HANDLE, LPSTR, LPSTR]
        self.send_command.restype = int

        self.close = self.dll.CohrHOPS_Close
        self.close.argtypes = [COHRHOPS_HANDLE]
        self.close.restype = int

        self.get_dll_version = self.dll.CohrHOPS_GetDLLVersion
        self.get_dll_version.argtypes = [LPSTR]
        self.get_dll_version.restype = int

        self.check_for_devices = self.dll.CohrHOPS_CheckForDevices
        self.check_for_devices.argtypes = [LPULPTR, LPDWORD, LPULPTR, LPDWORD, LPULPTR, LPDWORD]
        self.check_for_devices.restype = int


class HopsDevices:
    def __init__(self):
        # noinspection PyCallingNonCallable,PyTypeChecker
        self.devices = (COHRHOPS_HANDLE * MAX_DEVICES)()

    def __getitem__(self, index):
        return self.devices[index]

    def pointer(self):
        return self.devices


class HOPSDeviceManager:
    def __init__(self, dll_path=HOPS_DLL):
        self.dll = HOPSDLLWrapper(dll_path)
        self.devices = []
        self.initialize_devices()

    def __repr__(self):
        return f'HOPSDeviceManager with {len(self.devices)} devices: {self.devices}'

    @property
    def dll_version(self) -> str:
        buffer = C.create_string_buffer(MAX_STRLEN)
        res = self.dll.get_dll_version(buffer)
        if res == COHRHOPS_OK:
            return buffer.value.decode("utf-8")
        else:
            raise Exception(f'Error getting DLL version: {res}')

    def initialize_devices(self):
        devices_connected = HopsDevices()
        number_of_devices_connected = C.c_ulong()
        devices_added = HopsDevices()
        number_of_devices_added = C.c_ulong()
        devices_removed = HopsDevices()
        number_of_devices_removed = C.c_ulong()

        res = self.dll.check_for_devices(
            devices_connected.pointer(), C.byref(number_of_devices_connected),
            devices_added.pointer(), C.byref(number_of_devices_added),
            devices_removed.pointer(), C.byref(number_of_devices_removed)
        )

        if res != COHRHOPS_OK:
            raise Exception(f'Error checking for devices: {res}')

        if number_of_devices_connected.value > 0:
            for handle in devices_connected[:number_of_devices_connected.value]:
                print(f'Found device with handle {handle}')
                device = self.initialize_device(handle)
                self.devices.append(device)
        else:
            print('No devices connected')

    def initialize_device(self, handle: COHRHOPS_HANDLE) -> dict:
        headtype = C.create_string_buffer(MAX_STRLEN)
        res = self.dll.initialize_handle(handle, headtype)
        if res == COHRHOPS_OK:
            serial = self.get_device_serial(handle)
            print(f'Device {serial} initialized with handle {handle}')
            return {'serial': serial, 'handle': handle}
        else:
            raise Exception(f'Error initializing handle {handle}: {res}')

    def get_device_serial(self, handle: COHRHOPS_HANDLE) -> str:
        response = C.create_string_buffer(MAX_STRLEN)
        res = self.dll.send_command(handle, "?HID".encode("utf-8"), response)
        if res == COHRHOPS_OK:
            return response.value.decode("utf-8").strip()
        else:
            raise Exception(f'Error sending command to handle {handle}: {res}')


class HOPSDevice:
    _manager: Optional[HOPSDeviceManager] = None

    @classmethod
    def _initialize_manager(cls):
        if cls._manager is None:
            cls._manager = HOPSDeviceManager()

    def __init__(self, serial: str):
        self._initialize_manager()
        self.serial = serial
        print(self._manager)
        self.handle = self._get_handle()

    def _get_handle(self):
        if self._manager is not None:
            for device in self._manager.devices:
                if device['serial'] == self.serial:
                    return device['handle']
            raise ValueError(f'Device with serial number {self.serial} not found')

    def initialize(self):
        if self._manager is not None:
            res = self._manager.dll.initialize_handle(self.handle, self.serial.encode())
            if res != COHRHOPS_OK:
                raise Exception(f'Error initializing handle {self.handle}: {res}')

    def send_command(self, command: str) -> str:
        if self._manager is not None:
            response = C.create_string_buffer(MAX_STRLEN)
            res = self._manager.dll.send_command(self.handle, command.encode(), response)
            if res == COHRHOPS_OK:
                return response.value.decode("utf-8").strip()
            elif res == COHRHOPS_INVALID_COMMAND:
                raise ValueError(f'Invalid command: {command}')
            else:
                raise Exception(f'Error sending command to handle {self.handle}: {res}')
        else:
            raise ValueError('HOPs Manager not initialized')

    def close(self):
        if self._manager is not None:
            res = self._manager.dll.close(self.handle)
            if res != COHRHOPS_OK:
                raise Exception(f'Error closing handle {self.handle}: {res}')
