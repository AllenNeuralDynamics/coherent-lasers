/**************************************************************************
// Copyright (c) 2008-2017 Coherent Inc
//
// Description:
// DLL for using USB or RS-232 to control the Coherent HOPS lasers and
// power supplies.
//
//	2008-01-01 HL Initial release
//  2009-01-01 HL Add Linux code
//  2009-03-20 HL Add serial port code
//  2017-07-20 TW Fixes for 64-bit DLL on Windows 10
**************************************************************************/
#ifndef COHRHOPS_H
#define COHRHOPS_H

#if defined(_MSC_VER)  // Windows
#include <windows.h>

// This ifdef block allows this header to be used for
// either export or import of library functions.  For the
// DLL project, Visual Studio 2005 automatically defines
// COHRHOPS_EXPORTS in the command line (project-->Properties
// -->Configuration-->C/C++ -->Command Line).  For all
// other projects COHRHOPS_EXPORTS should be undefined.
#ifdef COHRHOPS_EXPORTS
#define COHRHOPS_API __declspec(dllexport)
#else
#define COHRHOPS_API __declspec(dllimport)
#endif

typedef UINT_PTR COHRHOPS_HANDLE;
#elif defined(__GNUC__)  // Linux
#include "WinTypes.h"
#define COHRHOPS_API
#define WINAPI
#define __declspec(X)

typedef long COHRHOPS_HANDLE;  // 32-bit int
#endif

// Avoid C++ name mangling (name decoration)
#ifdef __cplusplus
extern "C" {
#endif

// Error codes
#define COHRHOPS_OK 0
#define COHRHOPS_INVALID_HANDLE -1
#define COHRHOPS_INVALID_HEAD -2
#define COHRHOPS_INVALID_COMMAND -3
#define COHRHOPS_INVALID_DATA -4
#define COHRHOPS_I2C_ERROR -5
#define COHRHOPS_USB_ERROR -6
#define COHRHOPS_FTCI2C_DLL_FILE_NOT_FOUND -100
#define COHRHOPS_FTCI2C_DLL_FUNCTION_NOT_FOUND -101
#define COHRHOPS_FTCI2C_DLL_EXCEPTION -102
#define COHRHOPS_NXP_ERROR -200
#define COHRHOPS_RS232_ERROR -300
#define COHRHOPS_THREAD_ERROR -400
#define COHRHOPS_OTHER_ERROR -999

// Maximum number of USB HOPS power supplies plus devices
// containing similar USB chips or number of RS-232 HOPS
// power supplies
#define MAX_DEVICES 20

// All strings must be able to contain 100 characters
#define MAX_STRLEN 100

/**************************************************************************
CohrHOPS_CheckForDevices(...)
        Used for USB connections.  This function returns the number of devices
        connected, added and removed, and arrays of handles to these groups
        since the last call

CohrHOPS_OpenSerialPort(port, &handle)
        Used for RS-232 connections. 'port' is a string representing the RS-232
        port, and 'handle' is a 32-bit value.
        Linux: "/dev/ttyS0", "/dev/ttyUSB0"  A lockfile is created in /var/lock
        Windows: "COM1", "\\\\.\\COM19"  COM10 and higher require the
        special backslash notation.

CohrHOPS_InitializeHandle(handle, headType)
        Must be called with each handle obtained from CheckForDevices or
        OpenSerialPort before SendCommand.  This function determines what
        type of laser head is attached.

CohrHOPS_SendCommand(handle, command, response)
        Parses the ASCII command string, sends the binary command to the laser,
        and formats the binary response into a response string.

CohrHOPS_Close(handle)
        Closes handle obtained from CheckForDevices or OpenSerialPort.

CohrHOPS_GetDLLVersion(version)
        Gets the DLL version string

All functions return 0 for no error or a negative value for an error code.
**************************************************************************/

#ifdef _WIN32
typedef ULONG_PTR *LPULPTR;

INT32 WINAPI CohrHOPS_CheckForDevices(LPULPTR devicesConnected,
                                      LPDWORD numberOfDevicesConnected,
                                      LPULPTR devicesAdded,
                                      LPDWORD numberOfDevicesAdded,
                                      LPULPTR devicesRemoved,
                                      LPDWORD numberOfDevicesRemoved);
#else
COHRHOPS_API INT32 WINAPI CohrHOPS_CheckForDevices(
    LPDWORD arrayOfDevicesConnected, LPDWORD numberOfDevicesConnected,
    LPDWORD arrayOfDevicesAdded, LPDWORD numberOfDevicesAdded,
    LPDWORD arrayOfDevicesRemoved, LPDWORD numberOfDevicesRemoved);
#endif

COHRHOPS_API INT32 WINAPI CohrHOPS_OpenSerialPort(LPCSTR port,
                                                  COHRHOPS_HANDLE *handle);

COHRHOPS_API INT32 WINAPI CohrHOPS_InitializeHandle(COHRHOPS_HANDLE handle,
                                                    LPSTR headType);

COHRHOPS_API INT32 WINAPI CohrHOPS_SendCommand(COHRHOPS_HANDLE handle,
                                               LPSTR command, LPSTR response);

COHRHOPS_API INT32 WINAPI CohrHOPS_Close(COHRHOPS_HANDLE handle);

COHRHOPS_API INT32 WINAPI CohrHOPS_GetDLLVersion(LPSTR version);

#ifdef __cplusplus
}
#endif

#endif
