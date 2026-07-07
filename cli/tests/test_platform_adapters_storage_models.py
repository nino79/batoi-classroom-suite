from __future__ import annotations

import pytest
from pydantic import ValidationError

from bcs.platform.adapters.storage.models import (
    BlockDevice,
    FilesystemInfo,
    MountEntry,
    Partition,
    StorageConfiguration,
)


def _make_filesystem(**overrides: object) -> FilesystemInfo:
    defaults: dict[str, object] = {
        "fs_type": "vfat",
        "uuid": "AAAA-BBBB",
        "label": "ESP",
        "mount_options": "rw,relatime",
        "mount_point": "/boot/efi",
    }
    defaults.update(overrides)
    return FilesystemInfo(**defaults)  # type: ignore[arg-type]


def _make_partition(**overrides: object) -> Partition:
    defaults: dict[str, object] = {
        "name": "nvme0n1p1",
        "path": "/dev/nvme0n1p1",
        "number": 1,
        "size_bytes": 524288000,
        "partuuid": "11111111-1111-1111-1111-111111111111",
        "parttype": "C12A7328-F81F-11D2-BA4B-00A0C93EC93B",
        "filesystem": _make_filesystem(),
        "mount_point": "/boot/efi",
    }
    defaults.update(overrides)
    return Partition(**defaults)  # type: ignore[arg-type]


def _make_block_device(**overrides: object) -> BlockDevice:
    defaults: dict[str, object] = {
        "name": "nvme0n1",
        "path": "/dev/nvme0n1",
        "device_type": "disk",
        "size_bytes": 512110190592,
        "is_removable": False,
        "is_read_only": False,
        "is_nvme": True,
        "model": "Samsung SSD 980",
        "vendor": None,
        "serial": "S1234567890",
        "partitions": (_make_partition(),),
        "mount_point": None,
    }
    defaults.update(overrides)
    return BlockDevice(**defaults)  # type: ignore[arg-type]


def _make_mount_entry(**overrides: object) -> MountEntry:
    defaults: dict[str, object] = {
        "source": "/dev/nvme0n1p1",
        "target": "/boot/efi",
        "fstype": "vfat",
        "options": "rw,relatime",
        "parent": None,
    }
    defaults.update(overrides)
    return MountEntry(**defaults)  # type: ignore[arg-type]


def _make_configuration(**overrides: object) -> StorageConfiguration:
    defaults: dict[str, object] = {
        "devices": (_make_block_device(),),
        "mounts": (_make_mount_entry(),),
    }
    defaults.update(overrides)
    return StorageConfiguration(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# FilesystemInfo
# ---------------------------------------------------------------------------


def test_filesystem_construction_with_all_fields() -> None:
    fs = _make_filesystem()
    assert fs.fs_type == "vfat"
    assert fs.uuid == "AAAA-BBBB"
    assert fs.label == "ESP"
    assert fs.mount_options == "rw,relatime"
    assert fs.mount_point == "/boot/efi"


def test_filesystem_all_fields_default_to_none() -> None:
    fs = FilesystemInfo()
    assert fs.fs_type is None
    assert fs.uuid is None
    assert fs.label is None
    assert fs.mount_options is None
    assert fs.mount_point is None


def test_filesystem_populate_by_name_accepts_camel_case_aliases() -> None:
    fs = FilesystemInfo(
        fsType="ext4",
        uuid="deadbeef",
        label="root",
        mountOptions="rw",
        mountPoint="/",
    )
    assert fs.fs_type == "ext4"
    assert fs.mount_options == "rw"
    assert fs.mount_point == "/"


def test_filesystem_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FilesystemInfo.model_validate({"fsType": "vfat", "bogus": 1})


def test_filesystem_is_frozen() -> None:
    fs = _make_filesystem()
    with pytest.raises(ValidationError):
        fs.label = "changed"  # type: ignore[misc]


def test_filesystem_equality() -> None:
    assert _make_filesystem() == _make_filesystem()
    assert _make_filesystem(label="ESP") != _make_filesystem(label="other")


def test_filesystem_is_hashable() -> None:
    assert isinstance(hash(_make_filesystem()), int)


def test_filesystem_json_round_trip_uses_camel_case_aliases() -> None:
    fs = _make_filesystem()
    data = fs.model_dump(mode="json", by_alias=True)

    assert data["fsType"] == "vfat"
    assert data["mountOptions"] == "rw,relatime"
    assert data["mountPoint"] == "/boot/efi"
    assert "fs_type" not in data

    reloaded = FilesystemInfo.model_validate(data)
    assert reloaded == fs


# ---------------------------------------------------------------------------
# Partition
# ---------------------------------------------------------------------------


def test_partition_construction_with_all_fields() -> None:
    partition = _make_partition()
    assert partition.name == "nvme0n1p1"
    assert partition.path == "/dev/nvme0n1p1"
    assert partition.number == 1
    assert partition.size_bytes == 524288000
    assert partition.partuuid == "11111111-1111-1111-1111-111111111111"
    assert partition.parttype == "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"
    assert partition.filesystem is not None
    assert partition.filesystem.fs_type == "vfat"
    assert partition.mount_point == "/boot/efi"


def test_partition_optional_fields_default_to_none() -> None:
    partition = Partition(name="nvme0n1p1", path="/dev/nvme0n1p1", number=1)
    assert partition.size_bytes is None
    assert partition.partuuid is None
    assert partition.parttype is None
    assert partition.filesystem is None
    assert partition.mount_point is None


def test_partition_populate_by_name_accepts_camel_case_aliases() -> None:
    partition = Partition(
        name="nvme0n1p1",
        path="/dev/nvme0n1p1",
        number=1,
        sizeBytes=100,
        mountPoint="/boot/efi",
    )
    assert partition.size_bytes == 100
    assert partition.mount_point == "/boot/efi"


@pytest.mark.parametrize("number", [1, 2, 128])
def test_partition_accepts_valid_number(number: int) -> None:
    partition = _make_partition(number=number)
    assert partition.number == number


@pytest.mark.parametrize("number", [0, -1])
def test_partition_rejects_number_below_one(number: int) -> None:
    with pytest.raises(ValidationError):
        _make_partition(number=number)


def test_partition_accepts_zero_size() -> None:
    partition = _make_partition(size_bytes=0)
    assert partition.size_bytes == 0


def test_partition_rejects_negative_size() -> None:
    with pytest.raises(ValidationError):
        _make_partition(size_bytes=-1)


def test_partition_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Partition.model_validate(
            {"name": "nvme0n1p1", "path": "/dev/nvme0n1p1", "number": 1, "bogus": 1}
        )


def test_partition_requires_name_path_number() -> None:
    with pytest.raises(ValidationError):
        Partition.model_validate({"name": "nvme0n1p1"})


def test_partition_is_frozen() -> None:
    partition = _make_partition()
    with pytest.raises(ValidationError):
        partition.mount_point = "/mnt"  # type: ignore[misc]


def test_partition_equality() -> None:
    assert _make_partition() == _make_partition()
    assert _make_partition(number=1) != _make_partition(number=2)


def test_partition_is_hashable() -> None:
    assert isinstance(hash(_make_partition()), int)


def test_partition_json_round_trip_uses_camel_case_aliases() -> None:
    partition = _make_partition()
    data = partition.model_dump(mode="json", by_alias=True)

    assert data["sizeBytes"] == 524288000
    assert data["mountPoint"] == "/boot/efi"
    assert data["filesystem"]["fsType"] == "vfat"
    assert "size_bytes" not in data

    reloaded = Partition.model_validate(data)
    assert reloaded == partition


# ---------------------------------------------------------------------------
# BlockDevice
# ---------------------------------------------------------------------------


def test_block_device_construction_with_all_fields() -> None:
    device = _make_block_device()
    assert device.name == "nvme0n1"
    assert device.path == "/dev/nvme0n1"
    assert device.device_type == "disk"
    assert device.size_bytes == 512110190592
    assert device.is_removable is False
    assert device.is_read_only is False
    assert device.is_nvme is True
    assert device.model == "Samsung SSD 980"
    assert device.vendor is None
    assert device.serial == "S1234567890"
    assert len(device.partitions) == 1
    assert device.mount_point is None


def test_block_device_optional_fields_default() -> None:
    device = BlockDevice(
        name="loop0",
        path="/dev/loop0",
        device_type="loop",
        is_removable=False,
        is_read_only=True,
        is_nvme=False,
    )
    assert device.size_bytes is None
    assert device.model is None
    assert device.vendor is None
    assert device.serial is None
    assert device.partitions == ()
    assert device.mount_point is None


def test_block_device_populate_by_name_accepts_camel_case_aliases() -> None:
    device = BlockDevice(
        name="nvme0n1",
        path="/dev/nvme0n1",
        deviceType="disk",
        isRemovable=False,
        isReadOnly=False,
        isNvme=True,
    )
    assert device.device_type == "disk"
    assert device.is_removable is False
    assert device.is_nvme is True


def test_block_device_accepts_zero_size() -> None:
    device = _make_block_device(size_bytes=0)
    assert device.size_bytes == 0


def test_block_device_rejects_negative_size() -> None:
    with pytest.raises(ValidationError):
        _make_block_device(size_bytes=-1)


def test_block_device_accepts_partitions_with_distinct_numbers() -> None:
    device = _make_block_device(
        partitions=(
            _make_partition(name="nvme0n1p1", path="/dev/nvme0n1p1", number=1),
            _make_partition(name="nvme0n1p2", path="/dev/nvme0n1p2", number=2),
        )
    )
    assert len(device.partitions) == 2


def test_block_device_rejects_partitions_with_duplicate_numbers() -> None:
    with pytest.raises(ValidationError, match="duplicate number"):
        _make_block_device(
            partitions=(
                _make_partition(name="nvme0n1p1", path="/dev/nvme0n1p1", number=1),
                _make_partition(name="nvme0n1p1dup", path="/dev/nvme0n1p1dup", number=1),
            )
        )


def test_block_device_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BlockDevice.model_validate(
            {
                "name": "nvme0n1",
                "path": "/dev/nvme0n1",
                "deviceType": "disk",
                "isRemovable": False,
                "isReadOnly": False,
                "isNvme": True,
                "bogus": 1,
            }
        )


def test_block_device_requires_mandatory_fields() -> None:
    with pytest.raises(ValidationError):
        BlockDevice.model_validate({"name": "nvme0n1"})


def test_block_device_is_frozen() -> None:
    device = _make_block_device()
    with pytest.raises(ValidationError):
        device.model = "changed"  # type: ignore[misc]


def test_block_device_nested_partition_is_frozen() -> None:
    device = _make_block_device()
    with pytest.raises(ValidationError):
        device.partitions[0].mount_point = "/mnt"  # type: ignore[misc]


def test_block_device_equality() -> None:
    assert _make_block_device() == _make_block_device()
    assert _make_block_device(name="nvme0n1") != _make_block_device(name="nvme1n1")


def test_block_device_is_hashable() -> None:
    assert isinstance(hash(_make_block_device()), int)


def test_block_device_json_round_trip_uses_camel_case_aliases() -> None:
    device = _make_block_device()
    data = device.model_dump(mode="json", by_alias=True)

    assert data["deviceType"] == "disk"
    assert data["isRemovable"] is False
    assert data["isNvme"] is True
    assert data["partitions"][0]["name"] == "nvme0n1p1"
    assert "device_type" not in data

    reloaded = BlockDevice.model_validate(data)
    assert reloaded == device


# ---------------------------------------------------------------------------
# MountEntry
# ---------------------------------------------------------------------------


def test_mount_entry_construction_with_all_fields() -> None:
    entry = _make_mount_entry()
    assert entry.source == "/dev/nvme0n1p1"
    assert entry.target == "/boot/efi"
    assert entry.fstype == "vfat"
    assert entry.options == "rw,relatime"
    assert entry.parent is None


def test_mount_entry_parent_defaults_to_none() -> None:
    entry = MountEntry(source="tmpfs", target="/mnt/scratch", fstype="tmpfs", options="rw")
    assert entry.parent is None


def test_mount_entry_accepts_explicit_parent() -> None:
    entry = _make_mount_entry(parent="/boot/efi")
    assert entry.parent == "/boot/efi"


def test_mount_entry_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        MountEntry.model_validate(
            {
                "source": "tmpfs",
                "target": "/mnt/scratch",
                "fstype": "tmpfs",
                "options": "rw",
                "bogus": 1,
            }
        )


def test_mount_entry_requires_mandatory_fields() -> None:
    with pytest.raises(ValidationError):
        MountEntry.model_validate({"source": "tmpfs"})


def test_mount_entry_is_frozen() -> None:
    entry = _make_mount_entry()
    with pytest.raises(ValidationError):
        entry.target = "/mnt"  # type: ignore[misc]


def test_mount_entry_equality() -> None:
    assert _make_mount_entry() == _make_mount_entry()
    assert _make_mount_entry(target="/boot/efi") != _make_mount_entry(target="/mnt")


def test_mount_entry_is_hashable() -> None:
    assert isinstance(hash(_make_mount_entry()), int)


def test_mount_entry_json_round_trip() -> None:
    entry = _make_mount_entry()
    data = entry.model_dump(mode="json", by_alias=True)

    assert data["source"] == "/dev/nvme0n1p1"
    assert data["fstype"] == "vfat"

    reloaded = MountEntry.model_validate(data)
    assert reloaded == entry


# ---------------------------------------------------------------------------
# StorageConfiguration
# ---------------------------------------------------------------------------


def test_configuration_construction_with_all_fields() -> None:
    config = _make_configuration()
    assert len(config.devices) == 1
    assert config.devices[0].name == "nvme0n1"
    assert len(config.mounts) == 1
    assert config.mounts[0].target == "/boot/efi"


def test_configuration_defaults_to_empty() -> None:
    config = StorageConfiguration()
    assert config.devices == ()
    assert config.mounts == ()


def test_configuration_populate_by_name_accepts_camel_case_aliases() -> None:
    config = StorageConfiguration(devices=(_make_block_device(),), mounts=())
    assert len(config.devices) == 1


def test_configuration_accepts_devices_with_distinct_paths() -> None:
    config = _make_configuration(
        devices=(
            _make_block_device(name="nvme0n1", path="/dev/nvme0n1"),
            _make_block_device(name="sda", path="/dev/sda", is_nvme=False),
        )
    )
    assert len(config.devices) == 2


def test_configuration_rejects_devices_with_duplicate_paths() -> None:
    with pytest.raises(ValidationError, match="duplicate path"):
        _make_configuration(
            devices=(
                _make_block_device(name="nvme0n1", path="/dev/nvme0n1"),
                _make_block_device(name="nvme0n1dup", path="/dev/nvme0n1"),
            )
        )


def test_configuration_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        StorageConfiguration.model_validate({"devices": [], "mounts": [], "bogus": 1})


def test_configuration_is_frozen() -> None:
    config = _make_configuration()
    with pytest.raises(ValidationError):
        config.devices = ()  # type: ignore[misc]


def test_configuration_nested_device_is_frozen() -> None:
    config = _make_configuration()
    with pytest.raises(ValidationError):
        config.devices[0].name = "changed"  # type: ignore[misc]


def test_configuration_equality() -> None:
    assert _make_configuration() == _make_configuration()
    assert _make_configuration(mounts=()) != _make_configuration()


def test_configuration_is_hashable() -> None:
    """Every container field here is a tuple of frozen, hashable models,
    so the whole frozen model is hashable too - matching
    FirmwareBootConfiguration's own precedent.
    """
    assert isinstance(hash(_make_configuration()), int)


def test_configuration_json_round_trip_uses_camel_case_aliases() -> None:
    config = _make_configuration()
    data = config.model_dump(mode="json", by_alias=True)

    assert data["devices"][0]["deviceType"] == "disk"
    assert data["mounts"][0]["target"] == "/boot/efi"

    reloaded = StorageConfiguration.model_validate(data)
    assert reloaded == config


def test_configuration_json_round_trip_with_empty_defaults() -> None:
    config = StorageConfiguration()
    data = config.model_dump(mode="json", by_alias=True)
    assert data["devices"] == []
    assert data["mounts"] == []

    reloaded = StorageConfiguration.model_validate(data)
    assert reloaded == config
