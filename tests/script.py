#!/usr/bin/env python3
import logging
import time

from dotenv import load_dotenv

from coherent_lasers.genesis import GenesisMX
from coherent_lasers.hops.cohrhops import get_cohrhops_manager

logger = logging.getLogger("test_script")


def log_dll_version():
    manager = get_cohrhops_manager()
    logger.info(f"DLL Version: {manager.version}")


def validate_device_discovery(expected_serials: list[str]) -> tuple[list[str], list[str], list[str]]:
    manager = get_cohrhops_manager()
    serials = manager.discover()
    if not serials:
        logger.error("No devices discovered.")
    if missing := [serial for serial in expected_serials if serial not in serials]:
        logger.error(f"Missing devices: {missing}")
    if extra := [serial for serial in serials if serial not in expected_serials]:
        logger.error(f"Extra devices: {extra}")
    return serials, missing, extra


def create_devices(serials: list[str]) -> list[GenesisMX]:
    return [GenesisMX(serial) for serial in serials]


if __name__ == "__main__":
    import os

    load_dotenv()

    TEST_ITERATIONS = int(os.getenv("TEST_ITERATIONS", 1))
    GENESIS_MX_SERIALS = os.getenv("GENESIS_MX_SERIALS", "").split(",")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    logging.basicConfig(level=LOG_LEVEL)

    mrg = get_cohrhops_manager()

    logger.info(f"DLL Version: {mrg.version}")

    passes = 0
    total_time = 0
    q_total = 0
    qs = 0
    try:
        for i in range(TEST_ITERATIONS):
            print()
            logger.info(f"Starting iteration {i + 1}...")
            try:
                start_time = time.perf_counter()
                serials, missing, extra = validate_device_discovery(expected_serials=GENESIS_MX_SERIALS)
                logger.info(f"Discovered devices: {serials}")
                if extra:
                    logger.error(f"Extra devices not listed in .env: {extra}")
                if missing:
                    raise Exception(f"Missing devices: {missing}")

                create_start = time.perf_counter()
                devices = create_devices(serials=serials)
                for device in devices:
                    logger.info(f"{device.info.serial} created successfully.")
                logger.info(f"Created {len(devices)} devices in {time.perf_counter() - create_start:.2f} seconds.")

                for device in devices:
                    device.power = 50
                    device.enable()

                for device in devices:
                    device.await_power(20)

                q_all_start = time.perf_counter()
                for device in devices:
                    print()
                    logger.info(f"{device}.")
                    q_start = time.perf_counter()
                    logger.info(f"  - Remote Control: {device.remote_control}")
                    logger.info(f"  - key Switch: {device.key_switch}")
                    logger.info(f"  - interlock: {device.interlock}")
                    logger.info(f"  - software Switch: {device.software_switch}")
                    logger.info(f"  - Power: {device.power}")
                    logger.info(f"  - Main Temperature: {device.temperature}")
                    logger.info(f"  - LDD Current: {device.current}")
                    logger.info(f"  - Temperatures: {device.get_temperatures()}")
                    logger.info(f"  - Mode: {device.mode}")
                    logger.info(f"  - Alarms: {device.alarms}")
                    logger.info(f"  ---- Query time: {time.perf_counter() - q_start:.2f} seconds")
                    device.close()
                    q_total += time.perf_counter() - q_start
                    qs += 1
                print()
                time_taken = time.perf_counter() - start_time
                total_time += time_taken
                logger.info(f"Iteration {i + 1} completed in {time_taken:.2f} seconds.")
                logger.info(f"Total Query time: {time.perf_counter() - q_all_start:.2f} seconds")
                logger.info(f"Average Query time: {q_total / qs:.2f} seconds.") if qs else None
                print()
                passes += 1
            except Exception as e:
                logger.error(f"Test {i + 1} failed: {e}. ")
                continue
            finally:
                mrg.close()
                print()

    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
    finally:
        mrg.close()

    logger.info(f"  {passes}/{TEST_ITERATIONS} passes in {total_time:.2f} seconds.")
    logger.info(f"  Average time per iteration: {total_time / TEST_ITERATIONS:.2f} seconds.")
    print()
