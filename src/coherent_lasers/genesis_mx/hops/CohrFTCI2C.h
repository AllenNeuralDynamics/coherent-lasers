/*++

Copyright (c) 2005 Future Technology Devices International Ltd.

Module Name:

    ftcjtag.h

Abstract:

    API DLL for FT2232C Dual Device setup to simulate the I2C synchronous protocol.
    FTCI2C library definitions

Environment:

    kernel & user mode

Revision History:

    23/03/05    kra     Created.
	19/10/05	ana		removed control write if only 1 bytes to write
						fixed PAGE_WRITE acknowledge

	December 2008 HL (Coherent)
		Added Linux conditional compiling
		Added functions to open by SerialNumber
	July 2017 TW (Coherent)
		Changes for 64-bit DLL on Windows 10
--*/


#ifndef FTCI2C_H
#define FTCI2C_H

#ifndef _WIN32
// not used in Linux
#define WINAPI
#define __declspec(X)
#endif

// The following ifdef block is the standard way of creating macros
// which make exporting from a DLL simpler.  All files within this DLL
// are compiled with the FTCI2C_EXPORTS symbol defined on the command line.
// This symbol should not be defined on any project that uses this DLL.
// This way any other project whose source files include this file see
// FTCI2C_API functions as being imported from a DLL, whereas this DLL
// sees symbols defined with this macro as being exported.

#ifdef FTCI2C_EXPORTS
#define FTCI2C_API __declspec(dllexport)
#else
#define FTCI2C_API __declspec(dllimport)
#endif

#ifdef _WIN32
typedef ULONG_PTR FTC_HANDLE;
#else
typedef DWORD FTC_HANDLE;
#endif
typedef ULONG FTC_STATUS;

#define NO_WRITE_TYPE 0
#define BYTE_WRITE_TYPE 1
#define PAGE_WRITE_TYPE 2

#define BYTE_READ_TYPE 1
#define BLOCK_READ_TYPE 2

#define STANDARD_MODE 1
#define FAST_MODE 2
#define STRETCH_DATA_MODE 4

#define FTC_SUCCESS 0 // FT_OK
#define FTC_INVALID_HANDLE 1 // FT_INVALID_HANDLE
#define FTC_DEVICE_NOT_FOUND 2 //FT_DEVICE_NOT_FOUND
#define FTC_DEVICE_NOT_OPENED 3 //FT_DEVICE_NOT_OPENED
#define FTC_IO_ERROR 4 //FT_IO_ERROR
#define FTC_INSUFFICIENT_RESOURCES 5 // FT_INSUFFICIENT_RESOURCES

#define FTC_FAILED_TO_COMPLETE_COMMAND 20          // cannot change, error code mapped from FT2232c classes
#define FTC_FAILED_TO_SYNCHRONIZE_DEVICE_MPSSE 21  // cannot change, error code mapped from FT2232c classes
#define FTC_INVALID_DEVICE_NAME_INDEX 22           // cannot change, error code mapped from FT2232c classes
#define FTC_NULL_DEVICE_NAME_BUFFER_POINTER 23     // cannot change, error code mapped from FT2232c classes
#define FTC_DEVICE_NAME_BUFFER_TOO_SMALL 24        // cannot change, error code mapped from FT2232c classes
#define FTC_INVALID_DEVICE_NAME 25                 // cannot change, error code mapped from FT2232c classes
#define FTC_INVALID_LOCATION_ID 26                 // cannot change, error code mapped from FT2232c classes
#define FTC_DEVICE_IN_USE 27                       // cannot change, error code mapped from FT2232c classes
#define FTC_TOO_MANY_DEVICES 28                    // cannot change, error code mapped from FT2232c classes
#define FTC_EXTERNAL_DEVICE_NOT_FOUND 29
#define FTC_INVALID_CLOCK_DIVISOR 30
#define FTC_NULL_CONTROL_DATA_BUFFER_POINTER 31
#define FTC_INVALID_NUMBER_CONTROL_BYTES 32
#define FTC_CONTROL_ACKNOWLEDGE_TIMEOUT 33
#define FTC_NULL_WRITE_DATA_BUFFER_POINTER 34
#define FTC_INVALID_NUMBER_DATA_BYTES_WRITE 35
#define FTC_DATA_ACKNOWLEDGE_TIMEOUT 36
#define FTC_INVALID_WRITE_TYPE 37
#define FTC_NUMBER_BYTES_TOO_SMALL_PAGE_WRITE 38
#define FTC_NULL_PAGE_WRITE_BUFFER_POINTER 39
#define FTC_NULL_READ_DATA_BUFFER_POINTER 40
#define FTC_INVALID_NUMBER_DATA_BYTES_READ 41
#define FTC_INVALID_READ_TYPE 42
#define FTC_INVALID_COMMS_MODE 43
#define FTC_NULL_DLL_VERSION_BUFFER_POINTER 44
#define FTC_DLL_VERSION_BUFFER_TOO_SMALL 45
#define FTC_NULL_LANGUAGE_CODE_BUFFER_POINTER 46
#define FTC_NULL_ERROR_MESSAGE_BUFFER_POINTER 47
#define FTC_ERROR_MESSAGE_BUFFER_TOO_SMALL 48
#define FTC_INVALID_LANGUAGE_CODE 49
#define FTC_INVALID_STATUS_CODE 50

#ifdef __cplusplus
extern "C" {
#endif

FTCI2C_API
FTC_STATUS WINAPI I2C_GetNumDevices(LPDWORD lpdwNumDevices);

FTCI2C_API
FTC_STATUS WINAPI I2C_GetDeviceNameLocID(DWORD dwDeviceNameIndex, LPSTR lpDeviceNameBuffer, DWORD dwBufferSize, LPDWORD lpdwLocationID);

FTCI2C_API
FTC_STATUS WINAPI I2C_GetDeviceNameSerialNumber(DWORD dwDeviceNameIndex, LPSTR lpDeviceNameBuffer, DWORD dwBufferSize, LPSTR lpSerialNumber);

FTCI2C_API
FTC_STATUS WINAPI I2C_OpenEx(LPSTR lpDeviceName, DWORD dwLocationID, FTC_HANDLE *pftHandle);

FTCI2C_API
FTC_STATUS WINAPI I2C_OpenExSerialNumber(LPSTR lpDeviceName, LPSTR lpSerialNumber, FTC_HANDLE *pftHandle);

FTCI2C_API
FTC_STATUS WINAPI I2C_Open(FTC_HANDLE *pftHandle);

FTCI2C_API
FTC_STATUS WINAPI I2C_OpenSerialNumber(FTC_HANDLE *pftHandle);

FTCI2C_API
FTC_STATUS WINAPI I2C_Close(FTC_HANDLE ftHandle);

FTCI2C_API
FTC_STATUS WINAPI I2C_InitDevice(FTC_HANDLE ftHandle, DWORD dwClockDivisor);

FTCI2C_API
FTC_STATUS WINAPI I2C_GetClock(DWORD dwClockDivisor, LPDWORD lpdwClockFrequencyHz);

FTCI2C_API
FTC_STATUS WINAPI I2C_SetClock(FTC_HANDLE ftHandle, DWORD dwClockDivisor, LPDWORD lpdwClockFrequencyHz);

FTCI2C_API
FTC_STATUS WINAPI I2C_SetLoopback(FTC_HANDLE ftHandle, BOOL bLoopbackState);

FTCI2C_API
FTC_STATUS WINAPI I2C_SetMode(FTC_HANDLE ftHandle, DWORD dwCommsMode);

#define MAX_WRITE_CONTROL_BYTES_BUFFER_SIZE 256    // 256 bytes

typedef BYTE WriteControlByteBuffer[MAX_WRITE_CONTROL_BYTES_BUFFER_SIZE];
typedef WriteControlByteBuffer *PWriteControlByteBuffer;

typedef struct FTC_Page_Write_Data{
  DWORD  dwNumPages;
  DWORD  dwNumBytesPerPage;
}FTC_PAGE_WRITE_DATA, *PFTC_PAGE_WRITE_DATA;

#define MAX_WRITE_DATA_BYTES_BUFFER_SIZE 65536    // 64k bytes

typedef BYTE WriteDataByteBuffer[MAX_WRITE_DATA_BYTES_BUFFER_SIZE];
typedef WriteDataByteBuffer *PWriteDataByteBuffer;

FTCI2C_API
FTC_STATUS WINAPI I2C_Write(FTC_HANDLE ftHandle, PWriteControlByteBuffer pWriteControlBuffer,
                            DWORD dwNumControlBytesToWrite, BOOL bControlAcknowledge, DWORD dwControlAckTimeoutmSecs,
                            BOOL bStopCondition, DWORD dwDataWriteTypes, PWriteDataByteBuffer pWriteDataBuffer, DWORD dwNumDataBytesToWrite,
                            BOOL bDataAcknowledge, DWORD dwDataAckTimeoutmSecs, PFTC_PAGE_WRITE_DATA pPageWriteData);

#define MAX_READ_DATA_BYTES_BUFFER_SIZE 65536    // 64k bytes

typedef BYTE ReadDataByteBuffer[MAX_READ_DATA_BYTES_BUFFER_SIZE];
typedef ReadDataByteBuffer *PReadDataByteBuffer;

FTCI2C_API
FTC_STATUS WINAPI I2C_Read(FTC_HANDLE ftHandle, PWriteControlByteBuffer pWriteControlBuffer,
                           DWORD dwNumControlBytesToWrite, BOOL bControlAcknowledge, DWORD dwControlAckTimeoutmSecs,
                           DWORD dwDataReadTypes, PReadDataByteBuffer pReadDataBuffer, DWORD dwNumDataBytesToRead);

FTCI2C_API
FTC_STATUS WINAPI I2C_ReadAlt(FTC_HANDLE ftHandle, PWriteControlByteBuffer pWriteControlBuffer,
                           DWORD dwNumControlBytesToWrite, BOOL bControlAcknowledge, DWORD dwControlAckTimeoutmSecs,
                           DWORD dwDataReadTypes, PReadDataByteBuffer pReadDataBuffer, DWORD dwNumDataBytesToRead);

FTCI2C_API
FTC_STATUS WINAPI I2C_GetDllVersion(LPSTR lpDllVersionBuffer, DWORD dwBufferSize);

FTCI2C_API
FTC_STATUS WINAPI I2C_GetErrorCodeString(LPSTR lpLanguage, FTC_STATUS StatusCode,
                                         LPSTR lpErrorMessageBuffer, DWORD dwBufferSize);


#ifdef __cplusplus
}
#endif


#endif  /* FTCI2C_H */