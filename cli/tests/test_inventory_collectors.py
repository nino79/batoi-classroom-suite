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
# EFI System Partition
# ---------------------------------------------------------------------------


def test_esp_absent_when_proc_mounts_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(collectors, "_PROC_MOUNTS", tmp_path / "no-mounts")
    esp = collectors.collect_efi_system_partition()
    assert esp.present is False
    assert esp.mounted is False


def test_esp_absent_when_no_matching_mount(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mounts = tmp_path / "mounts"
    mounts.write_text("/dev/nvme0n1p2 / ext4 rw 0 0\n", encoding="utf-8")
    monkeypatch.setattr(collectors, "_PROC_MOUNTS", mounts)
    esp = collectors.collect_efi_system_partition()
    assert esp.present is False


def test_esp_present_and_mounted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mounts = tmp_path / "mounts"
    mounts.write_text(
        "/dev/nvme0n1p2 / ext4 rw 0 0\n/dev/nvme0n1p1 /boot/efi vfat rw 0 0\n",
        encoding="utf-8",
    )
    by_uuid_dir = tmp_path / "by-uuid"
    by_uuid_dir.mkdir()
    # A regular file stands in for a real ``/dev/disk/by-uuid`` symlink -
    # this exercises the resolved-path matching logic without needing
    # real symlink privileges in the test environment (production
    # entries are always symlinks; the matching code only cares about
    # the resolved path, not whether it got there via a symlink).
    partition_file = by_uuid_dir / "ABCD-1234"
    partition_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(collectors, "_PROC_MOUNTS", mounts)
    monkeypatch.setattr(collectors, "_DEV_DISK_BY_UUID", by_uuid_dir)

    def fake_realpath(path: object) -> str:
        return str(partition_file) if str(path) == "/dev/nvme0n1p1" else str(path)

    monkeypatch.setattr(collectors.os.path, "realpath", fake_realpath)

    class _FakeStatvfs:
        f_frsize = 512
        f_blocks = 1_000_000
        f_bavail = 500_000

    monkeypatch.setattr(collectors.os, "statvfs", lambda _path: _FakeStatvfs(), raising=False)

    esp = collectors.collect_efi_system_partition()
    assert esp.present is True
    assert esp.mounted is True
    assert esp.partition == "/dev/nvme0n1p1"
    assert esp.device == "/dev/nvme0n1"
    assert esp.filesystem == "vfat"
    assert esp.mount_point == "/boot/efi"
    assert esp.uuid == "ABCD-1234"
    assert esp.size_bytes == 512 * 1_000_000
    assert esp.free_bytes == 512 * 500_000


def test_parent_disk_returns_none_for_unrecognized_device_naming() -> None:
    assert collectors._parent_disk("/dev/mapper/vg-lv") is None


def test_partition_uuid_returns_none_when_realpath_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    by_uuid_dir = tmp_path / "by-uuid"
    by_uuid_dir.mkdir()
    monkeypatch.setattr(collectors, "_DEV_DISK_BY_UUID", by_uuid_dir)

    def raise_oserror(_path: object) -> str:
        raise OSError("boom")

    monkeypatch.setattr(collectors.os.path, "realpath", raise_oserror)
    assert collectors._partition_uuid("/dev/sda1") is None


def test_partition_usage_returns_none_when_statvfs_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_oserror(_path: object) -> object:
        raise OSError("boom")

    monkeypatch.setattr(collectors.os, "statvfs", raise_oserror, raising=False)
    assert collectors._partition_usage("/boot/efi") == (None, None)


def test_esp_sizes_none_when_statvfs_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mounts = tmp_path / "mounts"
    mounts.write_text("/dev/sda1 /boot/efi vfat rw 0 0\n", encoding="utf-8")
    monkeypatch.setattr(collectors, "_PROC_MOUNTS", mounts)
    monkeypatch.setattr(collectors, "_DEV_DISK_BY_UUID", tmp_path / "no-by-uuid")
    monkeypatch.delattr(collectors.os, "statvfs", raising=False)

    esp = collectors.collect_efi_system_partition()
    assert esp.present is True
    assert esp.device == "/dev/sda"
    assert esp.size_bytes is None
    assert esp.free_bytes is None
    assert esp.uuid is None


# ---------------------------------------------------------------------------
# USB storage
# ---------------------------------------------------------------------------


def test_usb_storage_empty_when_sys_block_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(collectors, "_SYS_BLOCK", tmp_path / "no-block")
    assert collectors.collect_usb_storage() == []


def test_usb_storage_finds_removable_usb_device_and_excludes_non_removable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    block_dir = tmp_path / "block"
    sdb_dir = block_dir / "sdb"
    device_dir = sdb_dir / "device"
    device_dir.mkdir(parents=True)
    (sdb_dir / "removable").write_text("1\n", encoding="utf-8")
    (sdb_dir / "size").write_text("31277232\n", encoding="utf-8")
    (device_dir / "vendor").write_text("SanDisk \n", encoding="utf-8")
    (device_dir / "model").write_text("Ultra\n", encoding="utf-8")

    # An internal, non-removable disk must be excluded.
    nvme_dir = block_dir / "nvme0n1"
    nvme_dir.mkdir()
    (nvme_dir / "removable").write_text("0\n", encoding="utf-8")

    monkeypatch.setattr(collectors, "_SYS_BLOCK", block_dir)
    monkeypatch.setattr(collectors, "_PROC_MOUNTS", tmp_path / "no-mounts")

    def fake_realpath(path: object) -> str:
        if str(path) == str(sdb_dir):
            return str(tmp_path / "pci0000" / "usb1" / "1-1" / "block" / "sdb")
        return str(path)

    monkeypatch.setattr(collectors.os.path, "realpath", fake_realpath)

    devices = collectors.collect_usb_storage()
    assert [d.name for d in devices] == ["sdb"]
    device = devices[0]
    assert device.path == "/dev/sdb"
    assert device.vendor == "SanDisk"
    assert device.model == "Ultra"
    assert device.size_bytes == 31277232 * 512
    assert device.mounted is False
    assert device.mount_point is None


def test_is_usb_removable_false_when_realpath_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    block_dir = tmp_path / "sdb"
    block_dir.mkdir()
    (block_dir / "removable").write_text("1\n", encoding="utf-8")

    def raise_oserror(_path: object) -> str:
        raise OSError("boom")

    monkeypatch.setattr(collectors.os.path, "realpath", raise_oserror)
    assert collectors._is_usb_removable(block_dir) is False


def test_usb_storage_excludes_removable_device_not_under_usb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A removable device (e.g. an internal SD card reader) that isn't
    actually USB-attached must not be reported as USB storage.
    """
    block_dir = tmp_path / "block"
    mmc_dir = block_dir / "mmcblk0"
    mmc_dir.mkdir(parents=True)
    (mmc_dir / "removable").write_text("1\n", encoding="utf-8")

    monkeypatch.setattr(collectors, "_SYS_BLOCK", block_dir)
    fake_path = str(tmp_path / "mmc_host0" / "block" / "mmcblk0")
    monkeypatch.setattr(collectors.os.path, "realpath", lambda _path: fake_path)

    assert collectors.collect_usb_storage() == []


def test_usb_storage_reports_mounted_partition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    block_dir = tmp_path / "block"
    sdb_dir = block_dir / "sdb"
    sdb_dir.mkdir(parents=True)
    (sdb_dir / "removable").write_text("1\n", encoding="utf-8")

    monkeypatch.setattr(collectors, "_SYS_BLOCK", block_dir)
    fake_path = str(tmp_path / "usb1" / "block" / "sdb")
    monkeypatch.setattr(collectors.os.path, "realpath", lambda _path: fake_path)

    mounts = tmp_path / "mounts"
    mounts.write_text("/dev/sdb1 /media/usb0 vfat rw 0 0\n", encoding="utf-8")
    monkeypatch.setattr(collectors, "_PROC_MOUNTS", mounts)

    devices = collectors.collect_usb_storage()
    assert devices[0].mounted is True
    assert devices[0].mount_point == "/media/usb0"


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
