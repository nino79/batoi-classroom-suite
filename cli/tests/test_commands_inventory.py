from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
import yaml

from bcs.commands import inventory as inventory_command
from bcs.inventory.models import (
    CpuInfo,
    EfiSystemPartition,
    FirmwareInfo,
    HostIdentity,
    HostInventory,
    MemoryInfo,
    NetworkInterface,
    OperatingSystemInfo,
    SecureBootState,
    StorageDevice,
    ToolStatus,
    UsbStorageDevice,
)
from bcs.output import OutputFormat


def _fake_inventory() -> HostInventory:
    return HostInventory(
        collectedAt=datetime.now(UTC),
        identity=HostIdentity(primaryMacAddress="aa:bb:cc:dd:ee:ff"),
        firmware=FirmwareInfo(uefi=True, secureBoot=SecureBootState.ENABLED),
        operatingSystem=OperatingSystemInfo(name="LliureX", architecture="x86_64"),
        cpu=CpuInfo(architecture="x86_64", logicalCores=4),
        memory=MemoryInfo(totalBytes=8 * 1024**3),
        efiSystemPartition=EfiSystemPartition(
            present=True,
            partition="/dev/nvme0n1p1",
            filesystem="vfat",
            mountPoint="/boot/efi",
            mounted=True,
        ),
        storage=[StorageDevice(name="nvme0n1", path="/dev/nvme0n1", isNvme=True)],
        usbStorage=[
            UsbStorageDevice(name="sdb", path="/dev/sdb", model="Ultra", mounted=False),
        ],
        network=[
            NetworkInterface(
                name="eth0", macAddress="aa:bb:cc:dd:ee:ff", isUp=True, isLoopback=False
            )
        ],
        tooling=[ToolStatus(name="clonezilla", found=True, path="/usr/bin/clonezilla")],
    )


@pytest.fixture
def patched_inventory(monkeypatch: pytest.MonkeyPatch) -> HostInventory:
    fake = _fake_inventory()
    monkeypatch.setattr(inventory_command, "collect_host_inventory", lambda: fake)
    return fake


def test_run_inventory_returns_zero(make_runtime_context, patched_inventory) -> None:
    runtime = make_runtime_context()
    assert inventory_command.run_inventory(runtime) == 0


def test_run_inventory_text_mentions_key_facts(make_runtime_context, patched_inventory) -> None:
    runtime = make_runtime_context(output=OutputFormat.TEXT)
    inventory_command.run_inventory(runtime)
    output = runtime.console.file.getvalue()  # type: ignore[attr-defined]
    assert "LliureX" in output
    assert "nvme0n1" in output
    assert "/boot/efi" in output
    assert "sdb" in output
    assert "eth0" in output
    assert "clonezilla" in output


def test_run_inventory_json_matches_model(make_runtime_context, patched_inventory) -> None:
    runtime = make_runtime_context(output=OutputFormat.JSON)
    inventory_command.run_inventory(runtime)
    payload = json.loads(runtime.console.file.getvalue())  # type: ignore[attr-defined]
    assert payload["schemaVersion"] == "bcs-inventory/v1alpha1"
    assert payload["operatingSystem"]["name"] == "LliureX"
    assert payload["efiSystemPartition"]["mountPoint"] == "/boot/efi"
    assert payload["usbStorage"][0]["name"] == "sdb"
    # The CLI's own schemaVersion must never shadow the inventory's own.
    assert payload["schemaVersion"] != "bcs-cli/v1alpha1"


def test_run_inventory_yaml_output(make_runtime_context, patched_inventory) -> None:
    runtime = make_runtime_context(output=OutputFormat.YAML)
    inventory_command.run_inventory(runtime)
    payload = yaml.safe_load(runtime.console.file.getvalue())  # type: ignore[attr-defined]
    assert payload["schemaVersion"] == "bcs-inventory/v1alpha1"
    assert payload["cpu"]["logicalCores"] == 4
