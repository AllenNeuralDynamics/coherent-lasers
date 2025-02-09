#!/usr/bin/env python3
import logging

from coherent_lasers.genesis import GenesisMX
from coherent_lasers.hops.cohrhops import get_cohrhops_manager

# Configure logger
logger = logging.getLogger("interactive_cli")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def discover_devices() -> list[str]:
    """Discover available laser devices and return their serial numbers."""
    manager = get_cohrhops_manager()
    serials = manager.discover()
    if not serials:
        logger.error("No devices discovered.")
    else:
        logger.info("Discovered devices:")
        for i, serial in enumerate(serials, start=1):
            logger.info(f"  {i}. {serial}")
    return serials


def select_devices(serials: list[str]) -> list[str]:
    """
    Present the discovered devices and ask the user to select one or more.
    Accepts comma-separated indices or the keyword "all".
    """
    print("\nEnter comma-separated numbers of devices to control (or type 'all' for all devices):")
    choice = input("> ").strip()
    if choice.lower() == "all":
        return serials
    try:
        indices = [int(x) for x in choice.split(",")]
        selected = [serials[i - 1] for i in indices if 0 < i <= len(serials)]
        if not selected:
            print("No valid selections made.")
        return selected
    except Exception as e:
        print(f"Error parsing selection: {e}")
        return []


def interactive_menu(devices: list[GenesisMX]):
    """
    Show an interactive menu for the selected devices.
    Commands are applied to all selected lasers.
    """
    menu = """
        Select an option:
        1. Show Device Info
        2. Show Power Status
        3. Set Power
        4. Enable Laser(s)
        5. Disable Laser(s)
        6. Show Detailed Status
        7. Quit
        Enter your choice:
        """

    while True:
        choice = input(menu).strip()
        if choice == "1":
            for device in devices:
                info = device.info
                print(f"\nDevice {info.serial}:")
                print(f"  Wavelength:     {info.wavelength} nm")
                print(f"  Head Type:      {info.head_type}")
                print(f"  Head Hours:     {info.head_hours}")
                print(f"  Board Revision: {info.head_board_revision}")
        elif choice == "2":
            for device in devices:
                power = device.power
                print(f"\nDevice {device.info.serial}:")
                print(f"  Current Power:  {power.value} mW")
                print(f"  Power Setpoint: {power.setpoint} mW")
        elif choice == "3":
            try:
                power_value = float(input("Enter desired power setpoint in mW: "))
                for device in devices:
                    device.power = power_value
                    device.await_power()
                    print(f"Device {device.info.serial}: Power set to {power_value} mW")
            except ValueError:
                print("Invalid power value.")
        elif choice == "4":
            for device in devices:
                print(f"Enabling device {device.info.serial}...")
                device.enable()
                print(f"Device {device.info.serial} enabled.")
        elif choice == "5":
            for device in devices:
                print(f"Disabling device {device.info.serial}...")
                device.disable()
                print(f"Device {device.info.serial} disabled.")
        elif choice == "6":
            for device in devices:
                print(f"\nDevice {device.info.serial} Detailed Status:")
                print(f"  Remote Control:   {device.remote_control}")
                print(f"  Key Switch:       {device.key_switch}")
                print(f"  Interlock:        {device.interlock}")
                print(f"  Software Switch:  {device.software_switch}")
                print(f"  Power:            {device.power}")
                print(f"  Main Temperature: {device.temperature} °C")
                print(f"  LDD Current:      {device.current} mA")
                print(f"  Temperatures:     {device.get_temperatures()}")
                print(f"  Mode:             {device.mode}")
                print(f"  Alarms:           {device.alarms}")
        elif choice == "7":
            print("Exiting interactive control...")
            break
        else:
            print("Invalid selection. Please try again.")


def main():
    # Discover devices using the CohrHOPS manager
    manager = get_cohrhops_manager()
    discovered_serials = discover_devices()
    if not discovered_serials:
        print("No devices discovered. Exiting.")
        manager.close()
        return

    # Display discovered devices with indices
    print("Discovered devices:")
    for i, serial in enumerate(discovered_serials, start=1):
        print(f"  {i}. {serial}")

    # Allow the user to select one or more devices by index
    selected_serials = select_devices(discovered_serials)
    if not selected_serials:
        print("No devices selected. Exiting.")
        manager.close()
        return

    # Create GenesisMX objects for each selected device
    devices = [GenesisMX(serial) for serial in selected_serials]
    print(f"\nControlling devices: {', '.join(selected_serials)}")

    try:
        interactive_menu(devices)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        # Ensure each device and the manager are properly closed.
        for device in devices:
            device.close()
        manager.close()


if __name__ == "__main__":
    main()
