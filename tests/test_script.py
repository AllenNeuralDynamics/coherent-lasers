#!/usr/bin/env python3
"""
Stress test for Coherent Genesis MX commands.
This script uses the CohrHOPSManager and CohrHOPSDevice classes
and the provided ReadCmds and WriteCmds enums to repeatedly
send commands to all discovered devices.
"""

import logging
import time

from dotenv import load_dotenv

from coherent_lasers.hops.cohrhops import get_cohrhops_manager
from coherent_lasers.genesis_mx.driver2 import GenesisMX

logger = logging.getLogger("lib2test")

for logger in [logger, get_cohrhops_manager().log]:
    logger.setLevel(logging.INFO)


def log_dll_version():
    manager = get_cohrhops_manager()
    logger.info(f"DLL Version: {manager.version}")


def test_discovery(expected_serials: list[str]) -> list[str]:
    manager = get_cohrhops_manager()
    serials = manager.discover()
    if not serials:
        logger.error("No devices discovered.")
    if missing := [serial for serial in expected_serials if serial not in serials]:
        logger.error(f"Missing devices: {missing}")
    if extra := [serial for serial in serials if serial not in expected_serials]:
        logger.error(f"Extra devices: {extra}")
    return serials


def create_devices(serials: list[str]) -> list[GenesisMX]:
    return [GenesisMX(serial) for serial in serials]


# def get_device_head_info(device: CohrHOPSDevice):
#     """Get the head type and serial number of a device."""
#     try:
#         head_type = device.send_read_command(ReadCmds.HEAD_TYPE)
#         head_serial = device.send_read_command(ReadCmds.HEAD_SERIAL)
#         return head_type, head_serial
#     except Exception as e:
#         logger.error(f"Error getting head info for device {device.serial}: {e}")
#         return None, None


if __name__ == "__main__":
    import os

    load_dotenv()

    GENESIS_MX_SERIALS = []

    if serials := os.getenv("GENESIS_MX_SERIALS"):
        GENESIS_MX_SERIALS = serials.split(",")

    mrg = get_cohrhops_manager()
    log_dll_version()

    iterations = 10
    passes = 0

    for i in range(iterations):
        logger.info(f"Starting stress test pass {i + 1}...")
        try:
            serials = test_discovery(expected_serials=GENESIS_MX_SERIALS)
            for device in create_devices(serials=serials):
                logger.info(f"{device} created successfully.")
            mrg.close()
            passes += 1
        except Exception as e:
            logger.error(f"Test {i + 1} failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
            continue

    logger.info(f"Test completed: {passes}/{iterations} passes.")
