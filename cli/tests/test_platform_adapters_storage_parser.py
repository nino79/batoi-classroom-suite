"""Tests for the pure Storage Adapter parser.

Per the fixture corpus's own placeholder rules
(``tests/fixtures/README.md``), the real corpus
(``tests/fixtures/storage/``) currently holds only zero-byte
placeholders for the three representative hardware scenarios named in
``docs/STORAGE_ADAPTER.md#testing-strategy`` - no real ``lsblk``/
``blkid``/``findmnt`` capture exists yet. These tests therefore build a
*temporary*, ``tmp_path``-rooted corpus (mirroring ``tests/fixtures/``'s
own layout) and load every scenario through ``fixture_utils.py``,
exactly as real captures will be loaded once they exist - never by
passing an inline string straight to the parser. The real corpus is
never written to.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from bcs.platform.adapters.storage.parser import parse_storage_topology
from fixture_utils import load_fixture

_EMPTY_LSBLK = '{"blockdevices": []}'
_EMPTY_BLKID = '{"blockdevices": []}'
_EMPTY_FINDMNT = '{"filesystems": []}'

# ---------------------------------------------------------------------------
# valid scenarios: scenario name -> {tool: raw JSON text}
# ---------------------------------------------------------------------------

_VALID_SCENARIOS: dict[str, dict[str, str]] = {
    "nvme-laptop-esp-root": {
        "lsblk": (
            '{"blockdevices": [{"name": "nvme0n1", "size": 512110190592, '
            '"type": "disk", "ro": false, "rm": false, "model": "Samsung SSD 980", '
            '"vendor": null, "serial": "S1234567890", "mountpoint": null, "children": ['
            '{"name": "nvme0n1p1", "size": 524288000, "mountpoint": "/boot/efi", "partn": 1}, '
            '{"name": "nvme0n1p2", "size": 511569084416, "mountpoint": "/", "partn": 2}'
            "]}]}"
        ),
        "blkid": (
            '{"blockdevices": ['
            '{"name": "/dev/nvme0n1p1", "type": "vfat", "uuid": "AAAA-BBBB", "label": null, '
            '"partuuid": "11111111-1111-1111-1111-111111111111", '
            '"parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"}, '
            '{"name": "/dev/nvme0n1p2", "type": "ext4", '
            '"uuid": "deadbeef-dead-beef-dead-beefdeadbeef", "label": "root", '
            '"partuuid": "22222222-2222-2222-2222-222222222222", '
            '"parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"}'
            "]}"
        ),
        "findmnt": (
            '{"filesystems": ['
            '{"target": "/boot/efi", "source": "/dev/nvme0n1p1", "fstype": "vfat", '
            '"options": "rw,relatime,fmask=0077,dmask=0077"}, '
            '{"target": "/", "source": "/dev/nvme0n1p2", "fstype": "ext4", '
            '"options": "rw,relatime"}'
            "]}"
        ),
    },
    "classroom-esp-root-home-swap": {
        "lsblk": (
            '{"blockdevices": [{"name": "nvme0n1", "size": 512110190592, "type": "disk", '
            '"ro": false, "rm": false, "model": "Classroom NVMe", "vendor": "Generic", '
            '"serial": "CL0001", "mountpoints": [null], "children": ['
            '{"name": "nvme0n1p1", "size": 524288000, "mountpoints": ["/boot/efi"], "partn": 1}, '
            '{"name": "nvme0n1p2", "size": 53687091200, "mountpoints": ["/"], "partn": 2}, '
            '{"name": "nvme0n1p3", "size": 107374182400, "mountpoints": ["/home"], "partn": 3}, '
            '{"name": "nvme0n1p4", "size": 4294967296, "mountpoints": [null], "partn": 4}'
            "]}]}"
        ),
        "blkid": (
            '{"blockdevices": ['
            '{"name": "/dev/nvme0n1p1", "type": "vfat", "uuid": "1111-2222", '
            '"partuuid": "aaaaaaaa-0000-0000-0000-000000000001", '
            '"parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"}, '
            '{"name": "/dev/nvme0n1p2", "type": "ext4", '
            '"uuid": "33333333-3333-3333-3333-333333333333", "label": "root", '
            '"partuuid": "aaaaaaaa-0000-0000-0000-000000000002", '
            '"parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"}, '
            '{"name": "/dev/nvme0n1p3", "type": "ext4", '
            '"uuid": "44444444-4444-4444-4444-444444444444", "label": "home", '
            '"partuuid": "aaaaaaaa-0000-0000-0000-000000000003", '
            '"parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"}, '
            '{"name": "/dev/nvme0n1p4", "type": "swap", '
            '"uuid": "55555555-5555-5555-5555-555555555555", '
            '"partuuid": "aaaaaaaa-0000-0000-0000-000000000004", '
            '"parttype": "0657fd6d-a4ab-43c4-84e5-0933c84b4f4f"}'
            "]}"
        ),
        "findmnt": (
            '{"filesystems": ['
            '{"target": "/boot/efi", "source": "/dev/nvme0n1p1", "fstype": "vfat", '
            '"options": "rw,relatime"}, '
            '{"target": "/", "source": "/dev/nvme0n1p2", "fstype": "ext4", '
            '"options": "rw,relatime"}, '
            '{"target": "/home", "source": "/dev/nvme0n1p3", "fstype": "ext4", '
            '"options": "rw,relatime"}, '
            '{"target": "/tmp", "source": "tmpfs", "fstype": "tmpfs", '
            '"options": "rw,nosuid,nodev"}'
            "]}"
        ),
    },
    "usb-recovery-drive": {
        "lsblk": (
            '{"blockdevices": [{"name": "sdb", "size": 32017047552, "type": "disk", '
            '"ro": false, "rm": true, "model": "Recovery USB", "vendor": "Generic", '
            '"serial": "USB0001", "mountpoint": null, "children": ['
            '{"name": "sdb1", "size": 32000000000, "mountpoint": null, "partn": 1}'
            "]}]}"
        ),
        "blkid": (
            '{"blockdevices": [{"name": "/dev/sdb1", "type": "vfat", "uuid": "6666-7777", '
            '"label": "RECOVERY", "partuuid": "bbbbbbbb-0000-0000-0000-000000000001", '
            '"parttype": "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"}]}'
        ),
        "findmnt": (
            '{"filesystems": [{"target": "/media/recovery", "source": "/dev/sdb1", '
            '"fstype": "vfat", "options": "rw,relatime,uid=1000"}]}'
        ),
    },
    "empty-topology": {
        "lsblk": _EMPTY_LSBLK,
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "whole-device-mount": {
        "lsblk": (
            '{"blockdevices": [{"name": "sdc", "size": 1000000000, "type": "disk", '
            '"ro": false, "rm": true, "mountpoint": null}]}'
        ),
        "blkid": _EMPTY_BLKID,
        "findmnt": (
            '{"filesystems": [{"target": "/mnt/whole", "source": "/dev/sdc", '
            '"fstype": "ext4", "options": "rw"}]}'
        ),
    },
    "bind-mount-nested": {
        "lsblk": (
            '{"blockdevices": [{"name": "nvme0n1", "size": 512110190592, "type": "disk", '
            '"ro": false, "rm": false, "mountpoint": null, "children": ['
            '{"name": "nvme0n1p2", "size": 511569084416, "mountpoint": "/", "partn": 2}'
            "]}]}"
        ),
        "blkid": _EMPTY_BLKID,
        "findmnt": (
            '{"filesystems": [{"target": "/", "source": "/dev/nvme0n1p2", "fstype": "ext4", '
            '"options": "rw", "children": [{"target": "/var/lib/docker", '
            '"source": "/dev/nvme0n1p2[/docker]", "fstype": "ext4", "options": "rw,bind"}]}]}'
        ),
    },
    "partn-fallback": {
        "lsblk": (
            '{"blockdevices": [{"name": "nvme0n1", "size": 512110190592, "type": "disk", '
            '"ro": false, "rm": false, "mountpoint": null, "children": ['
            '{"name": "nvme0n1p1", "size": 524288000, "mountpoint": "/boot/efi"}, '
            '{"name": "nvme0n1p2", "size": 511569084416, "mountpoint": "/"}'
            "]}]}"
        ),
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
}

# ---------------------------------------------------------------------------
# invalid scenarios: scenario name -> {tool: raw JSON text}, matched
# against the ValueError/ValidationError each one is expected to raise.
# ---------------------------------------------------------------------------

_INVALID_SCENARIOS: dict[str, dict[str, str]] = {
    "lsblk-invalid-json": {
        "lsblk": "{not valid json",
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "lsblk-missing-blockdevices": {"lsblk": "{}", "blkid": _EMPTY_BLKID, "findmnt": _EMPTY_FINDMNT},
    "lsblk-not-a-json-object": {"lsblk": "[]", "blkid": _EMPTY_BLKID, "findmnt": _EMPTY_FINDMNT},
    "lsblk-blockdevices-non-object-entry": {
        "lsblk": '{"blockdevices": ["oops"]}',
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "lsblk-device-missing-name": {
        "lsblk": '{"blockdevices": [{"type": "disk", "ro": false, "rm": false}]}',
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "lsblk-device-missing-type": {
        "lsblk": '{"blockdevices": [{"name": "nvme0n1", "ro": false, "rm": false}]}',
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "lsblk-device-missing-ro": {
        "lsblk": '{"blockdevices": [{"name": "nvme0n1", "type": "disk", "rm": false}]}',
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "lsblk-device-missing-rm": {
        "lsblk": '{"blockdevices": [{"name": "nvme0n1", "type": "disk", "ro": false}]}',
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "lsblk-children-not-list": {
        "lsblk": (
            '{"blockdevices": [{"name": "nvme0n1", "type": "disk", "ro": false, '
            '"rm": false, "children": "oops"}]}'
        ),
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "blkid-invalid-json": {
        "lsblk": _EMPTY_LSBLK,
        "blkid": "{not valid json",
        "findmnt": _EMPTY_FINDMNT,
    },
    "blkid-entry-missing-name": {
        "lsblk": _EMPTY_LSBLK,
        "blkid": '{"blockdevices": [{"type": "vfat"}]}',
        "findmnt": _EMPTY_FINDMNT,
    },
    "findmnt-invalid-json": {
        "lsblk": _EMPTY_LSBLK,
        "blkid": _EMPTY_BLKID,
        "findmnt": "{not valid json",
    },
    "findmnt-missing-filesystems": {"lsblk": _EMPTY_LSBLK, "blkid": _EMPTY_BLKID, "findmnt": "{}"},
    "findmnt-entry-missing-target": {
        "lsblk": _EMPTY_LSBLK,
        "blkid": _EMPTY_BLKID,
        "findmnt": '{"filesystems": [{"source": "/dev/sda1", "fstype": "ext4", "options": "rw"}]}',
    },
    "findmnt-children-not-list": {
        "lsblk": _EMPTY_LSBLK,
        "blkid": _EMPTY_BLKID,
        "findmnt": (
            '{"filesystems": [{"target": "/", "source": "/dev/sda1", "fstype": "ext4", '
            '"options": "rw", "children": "oops"}]}'
        ),
    },
    "duplicate-device-paths": {
        "lsblk": (
            '{"blockdevices": ['
            '{"name": "nvme0n1", "type": "disk", "ro": false, "rm": false}, '
            '{"name": "nvme0n1", "type": "disk", "ro": false, "rm": false}'
            "]}"
        ),
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
    "duplicate-partition-numbers": {
        "lsblk": (
            '{"blockdevices": [{"name": "nvme0n1", "type": "disk", "ro": false, "rm": false, '
            '"children": ['
            '{"name": "nvme0n1p1", "partn": 1}, '
            '{"name": "nvme0n1p1dup", "partn": 1}'
            "]}]}"
        ),
        "blkid": _EMPTY_BLKID,
        "findmnt": _EMPTY_FINDMNT,
    },
}


@pytest.fixture
def synthetic_corpus(tmp_path: Path) -> Path:
    """A temporary corpus, mirroring ``tests/fixtures/``'s own layout,
    holding synthetic-but-realistic scenarios for parser correctness
    only. Never writes to the real corpus.
    """
    valid_dir = tmp_path / "storage" / "valid"
    invalid_dir = tmp_path / "storage" / "invalid"
    valid_dir.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)
    for scenario, triple in _VALID_SCENARIOS.items():
        for tool, content in triple.items():
            (valid_dir / f"{tool}_test_ubuntu-24.04_{scenario}.txt").write_text(
                content, encoding="utf-8"
            )
    for scenario, triple in _INVALID_SCENARIOS.items():
        for tool, content in triple.items():
            (invalid_dir / f"{tool}_test_ubuntu-24.04_{scenario}.txt").write_text(
                content, encoding="utf-8"
            )
    return tmp_path


def _load_triple(root: Path, scenario: str, *, invalid: bool = False) -> tuple[str, str, str]:
    category = "invalid" if invalid else "valid"
    return (
        load_fixture("storage", category, f"lsblk_test_ubuntu-24.04_{scenario}.txt", root=root),
        load_fixture("storage", category, f"blkid_test_ubuntu-24.04_{scenario}.txt", root=root),
        load_fixture("storage", category, f"findmnt_test_ubuntu-24.04_{scenario}.txt", root=root),
    )


# ---------------------------------------------------------------------------
# well-formed scenarios
# ---------------------------------------------------------------------------


def test_nvme_laptop_esp_root(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "nvme-laptop-esp-root")
    config = parse_storage_topology(lsblk, blkid, findmnt)

    assert len(config.devices) == 1
    disk = config.devices[0]
    assert disk.name == "nvme0n1"
    assert disk.path == "/dev/nvme0n1"
    assert disk.device_type == "disk"
    assert disk.is_nvme is True
    assert disk.is_removable is False
    assert disk.model == "Samsung SSD 980"
    assert disk.serial == "S1234567890"
    assert len(disk.partitions) == 2

    esp, root = disk.partitions
    assert esp.number == 1
    assert esp.mount_point == "/boot/efi"
    assert esp.parttype == "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
    assert esp.filesystem is not None
    assert esp.filesystem.fs_type == "vfat"
    assert esp.filesystem.mount_point == "/boot/efi"
    assert esp.filesystem.mount_options == "rw,relatime,fmask=0077,dmask=0077"

    assert root.number == 2
    assert root.mount_point == "/"
    assert root.filesystem is not None
    assert root.filesystem.fs_type == "ext4"
    assert root.filesystem.label == "root"

    assert len(config.mounts) == 2
    assert {mount.target for mount in config.mounts} == {"/boot/efi", "/"}


def test_classroom_machine_multi_partition_and_mountpoints_array(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "classroom-esp-root-home-swap")
    config = parse_storage_topology(lsblk, blkid, findmnt)

    disk = config.devices[0]
    assert len(disk.partitions) == 4
    esp, root, home, swap = disk.partitions
    assert esp.mount_point == "/boot/efi"
    assert root.mount_point == "/"
    assert home.mount_point == "/home"
    # swap is never mounted - no findmnt entry references it
    assert swap.mount_point is None
    assert swap.filesystem is not None
    assert swap.filesystem.fs_type == "swap"

    # the device itself uses "mountpoints": [null] - not mounted
    assert disk.mount_point is None

    # tmpfs has no matching block device and still appears in the flat list
    assert any(mount.source == "tmpfs" for mount in config.mounts)
    assert len(config.mounts) == 4


def test_usb_recovery_drive(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "usb-recovery-drive")
    config = parse_storage_topology(lsblk, blkid, findmnt)

    disk = config.devices[0]
    assert disk.is_removable is True
    assert disk.is_nvme is False
    partition = disk.partitions[0]
    assert partition.mount_point == "/media/recovery"
    assert partition.filesystem is not None
    assert partition.filesystem.label == "RECOVERY"
    assert partition.filesystem.mount_point == "/media/recovery"


def test_empty_topology_yields_empty_configuration(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "empty-topology")
    config = parse_storage_topology(lsblk, blkid, findmnt)

    assert config.devices == ()
    assert config.mounts == ()


def test_whole_device_mount_and_absent_children_key(synthetic_corpus: Path) -> None:
    """A device with no 'children' key at all has no partitions, and a
    mount whose source matches the *device* path (not a partition) sets
    the device's own mount_point.
    """
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "whole-device-mount")
    config = parse_storage_topology(lsblk, blkid, findmnt)

    disk = config.devices[0]
    assert disk.partitions == ()
    assert disk.mount_point == "/mnt/whole"


def test_bind_mount_sets_parent_via_nested_children(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "bind-mount-nested")
    config = parse_storage_topology(lsblk, blkid, findmnt)

    assert len(config.mounts) == 2
    root_mount, bind_mount = config.mounts
    assert root_mount.parent is None
    assert bind_mount.target == "/var/lib/docker"
    assert bind_mount.parent == "/"


def test_partition_number_falls_back_to_array_position_without_partn(
    synthetic_corpus: Path,
) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "partn-fallback")
    config = parse_storage_topology(lsblk, blkid, findmnt)

    numbers = [partition.number for partition in config.devices[0].partitions]
    assert numbers == [1, 2]


@pytest.mark.parametrize("scenario", sorted(_VALID_SCENARIOS))
def test_every_valid_scenario_parses_without_error(synthetic_corpus: Path, scenario: str) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, scenario)
    parse_storage_topology(lsblk, blkid, findmnt)


# ---------------------------------------------------------------------------
# malformed input - rejected, not silently ignored
# ---------------------------------------------------------------------------


def test_lsblk_invalid_json_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "lsblk-invalid-json", invalid=True)
    with pytest.raises(ValueError, match=r"lsblk: output is not valid JSON"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_lsblk_missing_blockdevices_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(
        synthetic_corpus, "lsblk-missing-blockdevices", invalid=True
    )
    with pytest.raises(ValueError, match=r"lsblk: missing or non-list 'blockdevices'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_lsblk_non_object_top_level_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "lsblk-not-a-json-object", invalid=True)
    with pytest.raises(ValueError, match=r"lsblk: expected a JSON object at the top level"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_lsblk_blockdevices_non_object_entry_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(
        synthetic_corpus, "lsblk-blockdevices-non-object-entry", invalid=True
    )
    with pytest.raises(ValueError, match=r"'blockdevices' contains a non-object entry"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_lsblk_device_missing_name_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(
        synthetic_corpus, "lsblk-device-missing-name", invalid=True
    )
    with pytest.raises(ValueError, match=r"lsblk: missing or empty 'name'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_lsblk_device_missing_type_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(
        synthetic_corpus, "lsblk-device-missing-type", invalid=True
    )
    with pytest.raises(ValueError, match=r"lsblk: missing or empty 'type' for 'nvme0n1'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_lsblk_device_missing_ro_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "lsblk-device-missing-ro", invalid=True)
    with pytest.raises(ValueError, match=r"lsblk: missing or non-boolean 'ro'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_lsblk_device_missing_rm_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "lsblk-device-missing-rm", invalid=True)
    with pytest.raises(ValueError, match=r"lsblk: missing or non-boolean 'rm'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_lsblk_children_not_list_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "lsblk-children-not-list", invalid=True)
    with pytest.raises(ValueError, match=r"non-list 'children'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_blkid_invalid_json_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "blkid-invalid-json", invalid=True)
    with pytest.raises(ValueError, match=r"blkid: output is not valid JSON"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_blkid_entry_missing_name_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "blkid-entry-missing-name", invalid=True)
    with pytest.raises(ValueError, match=r"blkid: missing or empty 'name'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_findmnt_invalid_json_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "findmnt-invalid-json", invalid=True)
    with pytest.raises(ValueError, match=r"findmnt: output is not valid JSON"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_findmnt_missing_filesystems_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(
        synthetic_corpus, "findmnt-missing-filesystems", invalid=True
    )
    with pytest.raises(ValueError, match=r"findmnt: missing or non-list 'filesystems'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_findmnt_entry_missing_target_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(
        synthetic_corpus, "findmnt-entry-missing-target", invalid=True
    )
    with pytest.raises(ValueError, match=r"findmnt: missing or empty 'target'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_findmnt_children_not_list_is_rejected(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(
        synthetic_corpus, "findmnt-children-not-list", invalid=True
    )
    with pytest.raises(ValueError, match=r"non-list 'children'"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_duplicate_device_paths_raise_validation_error(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, "duplicate-device-paths", invalid=True)
    with pytest.raises(ValidationError, match="duplicate path"):
        parse_storage_topology(lsblk, blkid, findmnt)


def test_duplicate_partition_numbers_raise_validation_error(synthetic_corpus: Path) -> None:
    lsblk, blkid, findmnt = _load_triple(
        synthetic_corpus, "duplicate-partition-numbers", invalid=True
    )
    with pytest.raises(ValidationError, match="duplicate number"):
        parse_storage_topology(lsblk, blkid, findmnt)


@pytest.mark.parametrize("scenario", sorted(_INVALID_SCENARIOS))
def test_every_invalid_scenario_is_rejected(synthetic_corpus: Path, scenario: str) -> None:
    lsblk, blkid, findmnt = _load_triple(synthetic_corpus, scenario, invalid=True)
    with pytest.raises((ValueError, ValidationError)):
        parse_storage_topology(lsblk, blkid, findmnt)


# ---------------------------------------------------------------------------
# purity / independence
# ---------------------------------------------------------------------------


def test_parser_module_imports_nothing_but_stdlib_typing_and_its_own_models() -> None:
    """AST-based, not a substring search - this module's own docstring
    legitimately *discusses* subprocess/CommandRunner/errors as things
    it does not depend on, so a naive text search over the whole file
    would false-positive on its own documentation.
    """
    import ast

    import bcs.platform.adapters.storage.parser as parser_module

    source = Path(parser_module.__file__).read_text(encoding="utf-8")
    imported_modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden = {
        "subprocess",
        "typer",
        "rich",
        "bcs.platform.execution",
        "bcs.platform.errors",
        "bcs.platform.adapters.storage.errors",
        "bcs.context",
        "bcs.app",
    }
    assert not imported_modules & forbidden
    assert imported_modules == {
        "__future__",
        "json",
        "typing",
        "bcs.platform.adapters.storage.models",
    }
