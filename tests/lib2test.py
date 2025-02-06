#!/usr/bin/env python3
"""
Stress test for Coherent Genesis MX commands.
This script uses the CohrHOPSManager and CohrHOPSDevice classes
and the provided ReadCmds and WriteCmds enums to repeatedly
send commands to all discovered devices.
"""

import asyncio
import logging
import random

from coherent_lasers.hops.lib2 import get_cohrhops_manager, CohrHOPSDevice
from coherent_lasers.genesis_mx.commands import ReadCmds, WriteCmds
from dotenv import load_dotenv


# Configure logging for the stress test.
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("lib2test")
logger.setLevel(logging.INFO)


def log_dll_version():
    manager = get_cohrhops_manager()
    logger.info(f"DLL Version: {manager.version}")


def test_discovery(expected_serials: list[str]):
    manager = get_cohrhops_manager()
    serials = manager.discover()
    if not serials:
        logger.error("No devices discovered.")
        return
    if missing := [serial for serial in expected_serials if serial not in serials]:
        logger.error(f"Missing devices: {missing}")
    if extra := [serial for serial in serials if serial not in expected_serials]:
        logger.error(f"Extra devices: {extra}")


async def stress_test_device(device: CohrHOPSDevice, iterations: int = 100):
    """
    For a given device, send a random command from the ReadCmds repeatedly.
    Optionally, you can mix in some WriteCmds as well.
    """
    for i in range(iterations):
        # Randomly choose a read command.
        read_command = random.choice(
            [
                ReadCmds.HEAD_SERIAL.value,
                ReadCmds.HEAD_TYPE.value,
                ReadCmds.POWER.value,
                ReadCmds.POWER_SETPOINT.value,
                ReadCmds.LDD_CURRENT.value,
                ReadCmds.LDD_CURRENT_LIMIT.value,
                ReadCmds.MAIN_TEMPERATURE.value,
                ReadCmds.SHG_TEMPERATURE.value,
                ReadCmds.BRF_TEMPERATURE.value,
                ReadCmds.ETALON_TEMPERATURE.value,
                ReadCmds.INTERLOCK_STATUS.value,
                ReadCmds.KEY_SWITCH_STATE.value,
                ReadCmds.SOFTWARE_SWITCH_STATE.value,
                ReadCmds.REMOTE_CONTROL_STATUS.value,
            ]
        )
        try:
            response = await device.async_send_command(read_command)
            logger.info(f"[{device.serial}] Iteration {i}: {read_command} -> {response}")
        except Exception as e:
            logger.error(f"[{device.serial}] Iteration {i}: Command {read_command} failed: {e}")

        # Optionally, send a write command occasionally (e.g., 1 in 10 iterations)
        if i % 10 == 0:
            # Here we simulate a write command (for example, set remote control).
            # Adjust the command value and expected behavior as needed.
            write_command = WriteCmds.SET_REMOTE_CONTROL.value + "1"
            try:
                response = await device.async_send_command(write_command)
                logger.info(f"[{device.serial}] Iteration {i}: {write_command} -> {response}")
            except Exception as e:
                logger.error(f"[{device.serial}] Iteration {i}: Write command {write_command} failed: {e}")

        # Sleep a small random duration between iterations to vary the load.
        await asyncio.sleep(random.uniform(0.01, 0.05))


async def stress_test_all(iterations: int = 100):
    """
    Discover devices and run the stress test concurrently on all of them.
    """
    manager = get_cohrhops_manager()
    # Force a fresh discovery.
    try:
        serials = manager.discover()
    except Exception as e:
        logger.error("Discovery failed: %s", e)
        return

    if not serials:
        logger.error("No devices discovered. Exiting stress test.")
        return

    logger.info("DLL Version: %s", manager.version)
    logger.info("Discovered Devices: %s", serials)

    # Create a CohrHOPSDevice instance for each discovered serial.
    devices = [CohrHOPSDevice(serial) for serial in serials]
    # Create tasks for each device's stress test.
    tasks = [stress_test_device(device, iterations) for device in devices]
    # Run all tasks concurrently.
    await asyncio.gather(*tasks)
    # Close each device after testing.
    for device in devices:
        device.close()


if __name__ == "__main__":
    import os

    load_dotenv()

    GENESIS_MX_SERIALS = []

    if serials := os.getenv("GENESIS_MX_SERIALS"):
        GENESIS_MX_SERIALS = serials.split(",")

    log_dll_version()

    test_discovery(expected_serials=GENESIS_MX_SERIALS)

    # iterations = 0
    # start_time = time.time()
    # asyncio.run(stress_test_all(iterations))
    # end_time = time.time()
    # logger.info("Stress test completed in %.2f seconds", end_time - start_time)
