"""``bcs inventory`` - see ``docs/CLI.md#bcs-inventory``.

Collects a :class:`~bcs.inventory.models.HostInventory` snapshot and
renders it. This command does the *only* printing the Host Inventory
subsystem ever does - :mod:`bcs.inventory.collectors` and
:mod:`bcs.inventory.service` return data exclusively; formatting is
this module's job alone, per the subsystem's "never print directly"
requirement.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from bcs.context import RuntimeContext
from bcs.inventory.models import HostInventory
from bcs.inventory.service import collect_host_inventory
from bcs.output import OutputFormat, print_model_result


def _bool_text(value: bool) -> str:
    return "[green]yes[/green]" if value else "[red]no[/red]"


def _print_identity_and_firmware(console: Console, inventory: HostInventory) -> None:
    console.print("\n[bold]Identity[/bold]")
    console.print(
        f"  primary MAC address: {inventory.identity.primary_mac_address or '[dim]unknown[/dim]'}"
    )
    console.print(
        f"  DMI product UUID:    {inventory.identity.dmi_product_uuid or '[dim]unknown[/dim]'}"
    )

    console.print("\n[bold]Firmware[/bold]")
    console.print(f"  UEFI:        {_bool_text(inventory.firmware.uefi)}")
    console.print(f"  Secure Boot: {inventory.firmware.secure_boot.value}")


def _print_os_cpu_memory(console: Console, inventory: HostInventory) -> None:
    console.print("\n[bold]Operating System[/bold]")
    os_info = inventory.operating_system
    console.print(
        f"  {os_info.name} ({os_info.architecture}) - kernel {os_info.kernel or 'unknown'}"
    )

    console.print("\n[bold]CPU[/bold]")
    console.print(
        f"  {inventory.cpu.model or 'unknown model'} "
        f"({inventory.cpu.architecture}, {inventory.cpu.logical_cores or '?'} logical cores)"
    )

    console.print("\n[bold]Memory[/bold]")
    total = inventory.memory.total_bytes
    console.print(f"  total: {f'{total / (1024**3):.1f} GiB' if total else 'unknown'}")


def _print_efi_system_partition(console: Console, inventory: HostInventory) -> None:
    console.print("\n[bold]EFI System Partition[/bold]")
    esp = inventory.efi_system_partition
    if esp.present:
        console.print(
            f"  {esp.partition or 'unknown'} ({esp.filesystem or 'unknown'}), "
            f"mounted: {_bool_text(esp.mounted)}"
            + (f" at {esp.mount_point}" if esp.mount_point else "")
        )
    else:
        console.print("  [dim]not present[/dim]")


def _print_storage(console: Console, inventory: HostInventory) -> None:
    console.print("\n[bold]Storage[/bold]")
    if inventory.storage:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Device")
        table.add_column("NVMe")
        for device in inventory.storage:
            table.add_row(device.path, _bool_text(device.is_nvme))
        console.print(table)
    else:
        console.print("  [dim]no storage devices detected[/dim]")


def _print_usb_storage(console: Console, inventory: HostInventory) -> None:
    console.print("\n[bold]USB Storage[/bold]")
    if inventory.usb_storage:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Device")
        table.add_column("Model")
        table.add_column("Mounted")
        for device in inventory.usb_storage:
            table.add_row(device.path, device.model or "-", _bool_text(device.mounted))
        console.print(table)
    else:
        console.print("  [dim]no USB storage devices detected[/dim]")


def _print_network(console: Console, inventory: HostInventory) -> None:
    console.print("\n[bold]Network[/bold]")
    if inventory.network:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Interface")
        table.add_column("MAC")
        table.add_column("Up")
        for iface in inventory.network:
            table.add_row(iface.name, iface.mac_address or "-", _bool_text(iface.is_up))
        console.print(table)
    else:
        console.print("  [dim]no network interfaces detected[/dim]")


def _print_tooling(console: Console, inventory: HostInventory) -> None:
    console.print("\n[bold]Tooling[/bold]")
    for tool in inventory.tooling:
        console.print(
            f"  {tool.name}: {_bool_text(tool.found)}" + (f" ({tool.path})" if tool.path else "")
        )


def _print_text(runtime: RuntimeContext, inventory: HostInventory) -> None:
    console = runtime.console
    console.print(f"[bold]Host inventory[/bold] (collected {inventory.collected_at.isoformat()})")

    _print_identity_and_firmware(console, inventory)
    _print_os_cpu_memory(console, inventory)
    _print_efi_system_partition(console, inventory)
    _print_storage(console, inventory)
    _print_usb_storage(console, inventory)
    _print_network(console, inventory)
    _print_tooling(console, inventory)


def run_inventory(runtime: RuntimeContext) -> int:
    """Implement ``bcs inventory``. Returns the process exit code."""
    inventory = collect_host_inventory()

    if runtime.output is OutputFormat.TEXT:
        _print_text(runtime, inventory)
    else:
        print_model_result(runtime.console, runtime.output, inventory)

    return 0


__all__ = ["run_inventory"]
