"""
CLI Application for controlling and testing Genesis MX lasers.
Commands:
- list: list serial numbers of all connected devices
- device: send a subcommand to a specific device by serial number or interact with it in an interactive session
    - mode [PHOTO/CURRENT]: set the laser operation mode to PHOTO or CURRENT or display the current mode
    - power [value]: set the laser power to the specified value or display the current power
    - enable: enable the laser
    - disable: disable the laser
    - status: display the current status of the laser
    - stability_test [duration] [interval]: run a stability test on the laser for the specified duration and interval
    - help: display available commands
"""

import click
import time
import logging
from coherent_lasers.genesis_mx.driver import GenesisMX
from coherent_lasers.genesis_mx.commands import OperationModes, ReadCmds
from coherent_lasers.hops.lib import HOPSException, get_hops_manager

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@click.command()
def cli() -> None:
    manager = get_hops_manager()
    serials = manager._handles.values()
    devices = {serial: GenesisMX(serial) for serial in serials}
    click.echo(f"Found {len(serials)} devices:")
    if not devices:
        click.echo("No connected devices found.")
        return
    lasers = validate_lasers(devices)

    interactive_session(lasers)


def interactive_session(lasers: dict[str, GenesisMX]) -> None:
    """Start an interactive session with the devices."""
    exit = {"exit", "EXIT", "quit", "QUIT", ":q", ":Q"}
    select = {"select", "SELECT"}
    list_cmd = {"list", "ls"}
    lasers = lasers
    current = [next(iter(lasers.keys()))]
    click.echo(f"Starting interactive session with lasers: {', '.join(lasers.keys())}. Type 'exit' to end.")
    while True:
        command: str = click.prompt(f"{', '.join(current)}>", prompt_suffix="")
        command_parts = command.split()
        primary_command = command_parts[0].upper()
        if primary_command in exit:
            break
        if primary_command in list_cmd:
            click.echo(f"Found {len(lasers)} devices:")
            for serial in lasers:
                click.echo(f"  {serial}:")
            continue
        if primary_command in select:
            if len(command_parts) < 2:
                click.echo("Please provide a device to switch to. Either by index or serial number.")
                continue
            current = parse_select_command(command, lasers)
            continue
        run_command_on_lasers(lasers, current, command)


def parse_select_command(command: str, devices: dict) -> list:
    command_parts = command.upper().split()
    if "ALL" in command_parts:
        return list(devices.keys())
    selected = []
    for arg in command_parts:
        if arg.isdigit() and int(arg) <= len(devices):
            selected.append(list(devices.keys())[int(arg) - 1])
            continue
        if arg in devices:
            selected.append(arg)
            continue
    return selected


def validate_lasers(devices: dict[str, GenesisMX]) -> dict[str, GenesisMX]:
    """Validate that the devices are valid GenesisMX lasers by sending a test command."""
    lasers = {}
    head_types = {"MiniX", "Mini00"}
    for serial, device in devices.items():
        try:
            response = device.send_read_command(ReadCmds.HEAD_TYPE)
        except HOPSException as e:
            click.echo(f"Error getting head type for device {serial}: {str(e)}")
            continue
        if response.strip() in head_types:
            lasers[serial] = GenesisMX(serial)
    return lasers


def run_command_on_lasers(lasers: dict[str, GenesisMX], selected: list[str], command: str) -> None:
    try:
        if len(selected) == 1:
            handle_command(lasers[selected[0]], command)
            return
        for serial in selected:
            click.echo(f"  {serial} Laser -------------------------------------------------------------------------")
            handle_command(lasers[serial], command)
    except HOPSException as e:
        click.echo(f"Laser error: {e}")


def handle_command(device: GenesisMX, command: str) -> None:
    handlers = {
        "send": send_command,
        "enable": enable,
        "disable": disable,
        "info": info,
        "mode": mode,
        "power": power,
        "status": status,
        "help": display_help,
    }
    parts: list[str] = command.split()
    if not parts:
        return
    cmd: str = parts[0].lower()
    if cmd not in handlers:
        click.echo("Unknown command. Type 'help' for available commands.")
        return
    args = parts[1:]
    try:
        handlers[cmd](device, args)
    except Exception as e:
        click.echo(f"Error executing command: {str(e)}")


def enable(laser: GenesisMX, args=None) -> None:
    """Enable the laser."""
    if args:
        click.echo(f"    The enable command does not take any arguments, ignoring: {args}", nl=False)
    laser.enable()
    click.echo("Laser enabled.")


def disable(laser: GenesisMX, args=None) -> None:
    """Disable the laser."""
    if args:
        click.echo(f"    The disable command does not take any arguments, ignoring: {args}")
    laser.disable()
    click.echo("    Laser disabled.")


def info(laser: GenesisMX, args=None) -> None:
    """Display Laser Head information."""
    click.echo("  Laser Head info:")
    if args:
        click.echo(f"    The info command does not take any arguments, ignoring: {args}")
    try:
        info = laser.head
        click.echo(f"    Serial: {info.serial}", nl=False)
        click.echo(f"    Type: {info.type}", nl=False)
        click.echo(f"    Hours: {info.hours}", nl=False)
        click.echo(f"    Board Revision: {info.board_revision}", nl=False)
        click.echo(f"    DIO Status: {info.dio_status}")
    except Exception as e:
        click.echo(f"Error getting information: {str(e)}")


def mode(laser: GenesisMX, args=None) -> None:
    """Get or set the laser operation mode."""
    value = args[0] if args else None
    if value is not None:
        if value.upper() in OperationModes.__members__:
            laser.mode = OperationModes[value.upper()]
            click.echo("  Updating laser mode...")
    click.echo(f"    Mode: {laser.mode.name}, Valid modes: {' | '.join(OperationModes.__members__)}")


def power(laser: GenesisMX, args=[]) -> None:
    """Get or set the laser power."""
    wait = True
    value = None
    for arg in args:
        if arg == "--no-wait" or arg == "-nw":
            wait = False
        elif value is None:
            try:
                value = float(arg)
            except ValueError:
                click.echo(f"Invalid power value: {arg}")
                break
    if value is not None:
        laser.power_mw = value
        click.echo("  Updating laser power...")
        if wait:
            time.sleep(1)
    click.echo(f"    Power:             {laser.power_mw:.2f} mW")
    click.echo(f"    Power Setpoint:    {laser.power_setpoint_mw:.2f} mW")
    click.echo(f"    LDD Current:       {laser.ldd_current:.2f} A")
    click.echo(f"    LDD Current Limit: {laser.ldd_current_limit:.2f} A")


def status(laser: GenesisMX, args=None) -> None:
    """Display the current status of the laser."""
    full = "--full" in args or "-f" in args
    divider = "  ------------------------------------------------------------------------"
    if full:
        click.echo(divider)
        info(laser)
        click.echo(divider)
    enable_loop = laser.enable_loop
    click.echo("   Laser Status:")
    click.echo(f"    Software switch: {enable_loop.software}")
    click.echo(f"    Key switch: {enable_loop.key}")
    click.echo(f"    Interlock: {enable_loop.interlock}")
    click.echo(f"    LDD status: {laser.is_ldd_enabled}")
    click.echo(f"    Temperature: {laser.temperature_c:.2f} C")
    click.echo(f"    Alarms: {', '.join(alarm.name for alarm in laser.alarms)}")
    # click.echo(f"  Analog Input: {laser.analog_input_enable}")
    # click.echo(f"  Remote Control: {laser.remote_control_enable}")
    if full:
        click.echo(divider)
        mode(laser)
        click.echo(divider)
        power(laser)
        click.echo(divider)


def send_command(laser: GenesisMX, args=None) -> None:
    """Send a command to the laser."""
    if not args:
        click.echo("No command provided.")
        return
    command = args[0]
    response = laser.hops.send_command(command)
    click.echo(f"  Response: {response}")


def display_help(laser: GenesisMX, args=None) -> None:
    """Display available commands."""
    py_doc = "--full" in args or "-f" in args

    if laser is not None:
        click.echo(f"Available commands for laser {laser.serial}:")
    click.echo("Available commands:")
    click.echo("  --interactive, -i - Start an interactive session with the device")
    click.echo("      exit - End the interactive session")
    click.echo("  enable - Enable the laser")
    click.echo("  disable - Disable the laser")
    click.echo("  info - Display Laser Head information")
    click.echo("  mode [value] - Get or set the laser operation mode")
    click.echo("  power [value] [-nw|--no-wait] - Get or set the laser power")
    click.echo("  send [command] - Send a command to the laser")
    click.echo("  status [-f|--full] - Display the current status of the laser")
    click.echo("  help - Display this help message")
    if py_doc:
        click.echo(__doc__)


if __name__ == "__main__":
    cli(obj={})
