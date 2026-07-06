from __future__ import annotations

from pathlib import Path

import pytest

from bcs.inventory import collectors
from bcs.inventory.models import SecureBootState

# ---------------------------------------------------------------------------
# firmware / secure boot
# ---------------------------------------------------------------------------


def test_firmware_not_uefi_when_efi_dir_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(collectors, "_SYS_FIRMWARE_EFI", tmp_path / "no-such-efi")
    firmware = collectors.collect_firmware()
    assert firmware.uefi is False
    assert firmware.secure_boot is SecureBootState.UNSUPPORTED


def test_firmware_uefi_but_secure_boot_unknown_without_efivars(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    efi_dir = tmp_path / "efi"
    efi_dir.mkdir()
    monkeypatch.setattr(collectors, "_SYS_FIRMWARE_EFI", efi_dir)
    monkeypatch.setattr(collectors, "_SYS_FIRMWARE_EFIVARS", tmp_path / "efi" / "efivars-missing")
    firmware = collectors.collect_firmware()
    assert firmware.uefi is True
    assert firmware.secure_boot is SecureBootState.UNKNOWN


def test_firmware_uefi_with_efivars_present_is_still_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Secure Boot byte-value parsing is a documented placeholder gap."""
    efi_dir = tmp_path / "efi"
    efivars_dir = efi_dir / "efivars"
    efivars_dir.mkdir(parents=True)
    monkeypatch.setattr(collectors, "_SYS_FIRMWARE_EFI", efi_dir)
    monkeypatch.setattr(collectors, "_SYS_FIRMWARE_EFIVARS", efivars_dir)
    firmware = collectors.collect_firmware()
    assert firmware.uefi is True
    assert firmware.secure_boot is SecureBootState.UNKNOWN


# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------


def test_storage_empty_when_dev_absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(collectors, "_DEV", tmp_path / "no-dev")
    assert collectors.collect_storage() == []


def test_storage_finds_nvme_devices(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dev_dir = tmp_path / "dev"
    dev_dir.mkdir()
    (dev_dir / "nvme0n1").touch()
    (dev_dir / "nvme1n1").touch()
    (dev_dir / "sda").touch()  # not NVMe - must be excluded
    monkeypatch.setattr(collectors, "_DEV", dev_dir)

    devices = collectors.collect_storage()
    names = sorted(d.name for d in devices)
    assert names == ["nvme0n1", "nvme1n1"]
    assert all(d.is_nvme for d in devices)


# ---------------------------------------------------------------------------
# network
# ---------------------------------------------------------------------------


def _make_iface(net_dir: Path, name: str, *, mac: str | None, operstate: str) -> None:
    iface_dir = net_dir / name
    iface_dir.mkdir()
    if mac is not None:
        (iface_dir / "address").write_text(mac + "\n", encoding="utf-8")
    (iface_dir / "operstate").write_text(operstate + "\n", encoding="utf-8")


def test_network_empty_when_sys_class_net_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(collectors, "_SYS_CLASS_NET", tmp_path / "no-net")
    assert collectors.collect_network() == []


def test_network_enumerates_interfaces(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    net_dir = tmp_path / "net"
    net_dir.mkdir()
    _make_iface(net_dir, "lo", mac="00:00:00:00:00:00", operstate="unknown")
    _make_iface(net_dir, "eth0", mac="aa:bb:cc:dd:ee:ff", operstate="up")
    monkeypatch.setattr(collectors, "_SYS_CLASS_NET", net_dir)

    interfaces = {iface.name: iface for iface in collectors.collect_network()}
    assert interfaces["lo"].is_loopback is True
    assert interfaces["eth0"].is_loopback is False
    assert interfaces["eth0"].is_up is True
    assert interfaces["eth0"].mac_address == "aa:bb:cc:dd:ee:ff"
    assert interfaces["eth0"].ip_addresses == []


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------


def test_identity_skips_loopback_and_null_mac(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    net_dir = tmp_path / "net"
    net_dir.mkdir()
    _make_iface(net_dir, "lo", mac="00:00:00:00:00:00", operstate="unknown")
    _make_iface(net_dir, "eth0", mac="aa:bb:cc:dd:ee:ff", operstate="up")
    monkeypatch.setattr(collectors, "_SYS_CLASS_NET", net_dir)
    monkeypatch.setattr(collectors, "_SYS_CLASS_DMI_PRODUCT_UUID", tmp_path / "no-dmi")

    identity = collectors.collect_identity()
    assert identity.primary_mac_address == "aa:bb:cc:dd:ee:ff"
    assert identity.dmi_product_uuid is None


def test_identity_reads_dmi_product_uuid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uuid_path = tmp_path / "product_uuid"
    uuid_path.write_text("12345678-1234-1234-1234-123456789abc\n", encoding="utf-8")
    monkeypatch.setattr(collectors, "_SYS_CLASS_NET", tmp_path / "no-net")
    monkeypatch.setattr(collectors, "_SYS_CLASS_DMI_PRODUCT_UUID", uuid_path)

    identity = collectors.collect_identity()
    assert identity.dmi_product_uuid == "12345678-1234-1234-1234-123456789abc"


# ---------------------------------------------------------------------------
# operating system / memory / cpu
# ---------------------------------------------------------------------------


def test_operating_system_prefers_os_release_pretty_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    os_release = tmp_path / "os-release"
    os_release.write_text('PRETTY_NAME="LliureX 23"\nNAME="LliureX"\n', encoding="utf-8")
    monkeypatch.setattr(collectors, "_ETC_OS_RELEASE", os_release)

    info = collectors.collect_operating_system()
    assert info.name == "LliureX 23"
    assert info.architecture  # platform.machine() always returns something


def test_operating_system_falls_back_without_os_release(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(collectors, "_ETC_OS_RELEASE", tmp_path / "no-os-release")
    info = collectors.collect_operating_system()
    assert info.name  # falls back to platform.system()


def test_memory_absent_meminfo_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(collectors, "_PROC_MEMINFO", tmp_path / "no-meminfo")
    memory = collectors.collect_memory()
    assert memory.total_bytes is None
    assert memory.available_bytes is None


def test_memory_parses_meminfo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:       16384000 kB\nMemAvailable:    8192000 kB\n", encoding="utf-8"
    )
    monkeypatch.setattr(collectors, "_PROC_MEMINFO", meminfo)

    memory = collectors.collect_memory()
    assert memory.total_bytes == 16384000 * 1024
    assert memory.available_bytes == 8192000 * 1024


def test_cpu_model_absent_cpuinfo_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(collectors, "_PROC_CPUINFO", tmp_path / "no-cpuinfo")
    cpu = collectors.collect_cpu()
    assert cpu.model is None
    assert cpu.architecture


def test_cpu_model_parses_cpuinfo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(
        "processor\t: 0\nmodel name\t: Test CPU 3000\nflags\t\t: fpu\n", encoding="utf-8"
    )
    monkeypatch.setattr(collectors, "_PROC_CPUINFO", cpuinfo)

    cpu = collectors.collect_cpu()
    assert cpu.model == "Test CPU 3000"


# ---------------------------------------------------------------------------
# tooling
# ---------------------------------------------------------------------------


def test_tooling_reports_missing_and_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        return "/usr/bin/clonezilla" if name == "clonezilla" else None

    monkeypatch.setattr(collectors.shutil, "which", fake_which)
    statuses = {tool.name: tool for tool in collectors.collect_tooling(("clonezilla", "partclone"))}
    assert statuses["clonezilla"].found is True
    assert statuses["clonezilla"].path == "/usr/bin/clonezilla"
    assert statuses["partclone"].found is False
    assert statuses["partclone"].path is None
