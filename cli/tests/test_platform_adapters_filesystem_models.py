from __future__ import annotations

import pytest
from pydantic import ValidationError

from bcs.platform.adapters.filesystem.models import FilesystemUsage, FilesystemUsageReport


def _make_usage(**overrides: object) -> FilesystemUsage:
    defaults: dict[str, object] = {
        "source": "/dev/nvme0n1p2",
        "target": "/",
        "fs_type": "ext4",
        "size_bytes": 512110190592,
        "used_bytes": 128027547648,
        "available_bytes": 358486736896,
        "inodes_total": 32768000,
        "inodes_used": 512000,
        "inodes_available": 32256000,
        "raw_line": (
            "/dev/nvme0n1p2 ext4 32768000 512000 32256000 512110190592 128027547648 358486736896 /"
        ),
    }
    defaults.update(overrides)
    return FilesystemUsage(**defaults)  # type: ignore[arg-type]


def _make_report(**overrides: object) -> FilesystemUsageReport:
    defaults: dict[str, object] = {
        "filesystems": (_make_usage(),),
        "raw_text": "source fstype ... \n/dev/nvme0n1p2 ext4 ... /\n",
    }
    defaults.update(overrides)
    return FilesystemUsageReport(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# FilesystemUsage: construction / defaults
# ---------------------------------------------------------------------------


def test_usage_construction_with_all_fields() -> None:
    usage = _make_usage()
    assert usage.source == "/dev/nvme0n1p2"
    assert usage.target == "/"
    assert usage.fs_type == "ext4"
    assert usage.size_bytes == 512110190592
    assert usage.used_bytes == 128027547648
    assert usage.available_bytes == 358486736896
    assert usage.inodes_total == 32768000
    assert usage.inodes_used == 512000
    assert usage.inodes_available == 32256000
    assert usage.raw_line.startswith("/dev/nvme0n1p2")


def test_usage_inode_fields_default_to_none() -> None:
    """None means df -i-equivalent reporting is not meaningful for this
    filesystem type (df's own '-' token) - a normal condition, not an
    error - see docs/FILESYSTEM_ADAPTER.md#domain-models.
    """
    usage = _make_usage(inodes_total=None, inodes_used=None, inodes_available=None)
    assert usage.inodes_total is None
    assert usage.inodes_used is None
    assert usage.inodes_available is None


def test_usage_minimal_construction_omitting_optional_inode_fields() -> None:
    usage = FilesystemUsage(
        source="tmpfs",
        target="/run",
        fs_type="tmpfs",
        size_bytes=1073741824,
        used_bytes=1245184,
        available_bytes=1072496640,
        raw_line="tmpfs tmpfs - - - 1073741824 1245184 1072496640 /run",
    )
    assert usage.inodes_total is None
    assert usage.inodes_used is None
    assert usage.inodes_available is None


def test_usage_target_may_contain_internal_whitespace() -> None:
    usage = _make_usage(target="/media/USB DRIVE")
    assert usage.target == "/media/USB DRIVE"


def test_usage_populate_by_name_accepts_camel_case_aliases() -> None:
    usage = FilesystemUsage(
        source="/dev/nvme0n1p1",
        target="/boot/efi",
        fsType="vfat",
        sizeBytes=524288000,
        usedBytes=104857600,
        availableBytes=419430400,
        inodesTotal=None,
        inodesUsed=None,
        inodesAvailable=None,
        rawLine="/dev/nvme0n1p1 vfat - - - 524288000 104857600 419430400 /boot/efi",
    )
    assert usage.fs_type == "vfat"
    assert usage.size_bytes == 524288000
    assert usage.used_bytes == 104857600
    assert usage.available_bytes == 419430400


# ---------------------------------------------------------------------------
# FilesystemUsage: validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    ["size_bytes", "used_bytes", "available_bytes"],
)
def test_usage_rejects_negative_required_byte_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        _make_usage(**{field: -1})


@pytest.mark.parametrize(
    "field",
    ["inodes_total", "inodes_used", "inodes_available"],
)
def test_usage_rejects_negative_optional_inode_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        _make_usage(**{field: -1})


def test_usage_accepts_zero_for_every_numeric_field() -> None:
    usage = _make_usage(
        size_bytes=0,
        used_bytes=0,
        available_bytes=0,
        inodes_total=0,
        inodes_used=0,
        inodes_available=0,
    )
    assert usage.size_bytes == 0
    assert usage.inodes_total == 0


def test_usage_does_not_require_used_plus_available_to_equal_size() -> None:
    """Deliberately not validated - reserved filesystem blocks (e.g.
    ext4's default 5% root reservation) routinely make this arithmetic
    not hold for perfectly healthy, real filesystems - see
    docs/FILESYSTEM_ADAPTER.md#domain-models.
    """
    usage = _make_usage(size_bytes=1000, used_bytes=100, available_bytes=850)
    assert usage.size_bytes == 1000
    assert usage.used_bytes == 100
    assert usage.available_bytes == 850


def test_usage_does_not_require_used_to_be_at_most_size() -> None:
    """Deliberately not validated - a filesystem in the middle of a
    write, or one using overlay/reflink accounting, can transiently
    report figures that don't obey this inequality cleanly.
    """
    usage = _make_usage(size_bytes=1000, used_bytes=1200, available_bytes=0)
    assert usage.used_bytes == 1200


def test_usage_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FilesystemUsage.model_validate(
            {
                "source": "/dev/nvme0n1p2",
                "target": "/",
                "fsType": "ext4",
                "sizeBytes": 100,
                "usedBytes": 50,
                "availableBytes": 50,
                "rawLine": "...",
                "bogus": 1,
            }
        )


@pytest.mark.parametrize(
    "field",
    ["source", "target", "fs_type", "size_bytes", "used_bytes", "available_bytes", "raw_line"],
)
def test_usage_requires_mandatory_fields(field: str) -> None:
    data: dict[str, object] = {
        "source": "/dev/nvme0n1p2",
        "target": "/",
        "fsType": "ext4",
        "sizeBytes": 100,
        "usedBytes": 50,
        "availableBytes": 50,
        "rawLine": "...",
    }
    alias_map = {
        "fs_type": "fsType",
        "size_bytes": "sizeBytes",
        "used_bytes": "usedBytes",
        "available_bytes": "availableBytes",
        "raw_line": "rawLine",
    }
    del data[alias_map.get(field, field)]
    with pytest.raises(ValidationError):
        FilesystemUsage.model_validate(data)


# ---------------------------------------------------------------------------
# FilesystemUsage: immutability / equality / hashing
# ---------------------------------------------------------------------------


def test_usage_is_frozen() -> None:
    usage = _make_usage()
    with pytest.raises(ValidationError):
        usage.used_bytes = 0  # type: ignore[misc]


def test_usage_equality() -> None:
    assert _make_usage() == _make_usage()
    assert _make_usage(target="/") != _make_usage(target="/home")


def test_usage_is_hashable() -> None:
    assert isinstance(hash(_make_usage()), int)


# ---------------------------------------------------------------------------
# FilesystemUsage: serialization / deserialization
# ---------------------------------------------------------------------------


def test_usage_json_round_trip_uses_camel_case_aliases() -> None:
    usage = _make_usage()
    data = usage.model_dump(mode="json", by_alias=True)

    assert data["fsType"] == "ext4"
    assert data["sizeBytes"] == usage.size_bytes
    assert data["usedBytes"] == usage.used_bytes
    assert data["availableBytes"] == usage.available_bytes
    assert data["inodesTotal"] == usage.inodes_total
    assert data["inodesUsed"] == usage.inodes_used
    assert data["inodesAvailable"] == usage.inodes_available
    assert data["rawLine"] == usage.raw_line
    assert "fs_type" not in data
    assert "size_bytes" not in data

    reloaded = FilesystemUsage.model_validate(data)
    assert reloaded == usage


def test_usage_json_round_trip_with_none_inode_fields() -> None:
    usage = _make_usage(inodes_total=None, inodes_used=None, inodes_available=None)
    data = usage.model_dump(mode="json", by_alias=True)
    assert data["inodesTotal"] is None
    assert data["inodesUsed"] is None
    assert data["inodesAvailable"] is None

    reloaded = FilesystemUsage.model_validate(data)
    assert reloaded == usage


# ---------------------------------------------------------------------------
# FilesystemUsageReport: construction / defaults
# ---------------------------------------------------------------------------


def test_report_construction_with_filesystems() -> None:
    report = _make_report()
    assert len(report.filesystems) == 1
    assert report.filesystems[0].target == "/"
    assert report.raw_text.startswith("source fstype")


def test_report_filesystems_defaults_to_empty_tuple() -> None:
    report = FilesystemUsageReport(raw_text="")
    assert report.filesystems == ()
    assert isinstance(report.filesystems, tuple)


def test_report_raw_stderr_defaults_to_empty_string() -> None:
    """parse_filesystem_usage itself always leaves this at its default -
    the parser only ever sees stdout; attaching the real value is
    adapter.py's job - see docs/FILESYSTEM_ADAPTER.md#domain-models.
    """
    report = _make_report()
    assert report.raw_stderr == ""


def test_report_raw_stderr_can_be_set_explicitly() -> None:
    report = _make_report(raw_stderr="df: '/mnt/stale': Stale file handle")
    assert report.raw_stderr == "df: '/mnt/stale': Stale file handle"


def test_report_populate_by_name_accepts_camel_case_aliases() -> None:
    report = FilesystemUsageReport(
        filesystems=(_make_usage(),),
        rawText="raw df output\n",
        rawStderr="",
    )
    assert report.raw_text == "raw df output\n"
    assert report.raw_stderr == ""


# ---------------------------------------------------------------------------
# FilesystemUsageReport: validation
# ---------------------------------------------------------------------------


def test_report_does_not_reject_duplicate_target_entries() -> None:
    """Deliberately not validated: mount stacking (overmounting) can
    legitimately list the same target more than once - this is a real
    machine state, not a data error, and rejecting or silently
    deduplicating it would violate this adapter's "expose facts, never
    hide them" mandate - see docs/FILESYSTEM_ADAPTER.md#domain-models.
    """
    first = _make_usage(source="/dev/nvme0n1p2", target="/mnt/shared")
    second = _make_usage(source="tmpfs", target="/mnt/shared")

    report = FilesystemUsageReport(filesystems=(first, second), raw_text="...")

    assert len(report.filesystems) == 2
    assert report.filesystems[0].target == report.filesystems[1].target == "/mnt/shared"
    assert report.filesystems[0] != report.filesystems[1]


def test_report_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FilesystemUsageReport.model_validate({"rawText": "", "bogus": 1})


def test_report_requires_raw_text() -> None:
    with pytest.raises(ValidationError):
        FilesystemUsageReport.model_validate({})


# ---------------------------------------------------------------------------
# FilesystemUsageReport: immutability / equality / hashing
# ---------------------------------------------------------------------------


def test_report_is_frozen() -> None:
    report = _make_report()
    with pytest.raises(ValidationError):
        report.raw_text = "changed"  # type: ignore[misc]


def test_report_nested_filesystem_entries_are_frozen() -> None:
    report = _make_report()
    with pytest.raises(ValidationError):
        report.filesystems[0].used_bytes = 0  # type: ignore[misc]


def test_report_equality() -> None:
    assert _make_report() == _make_report()
    assert _make_report(raw_stderr="x") != _make_report()


def test_report_is_hashable() -> None:
    """Unlike HostDiscoverySnapshot, every field here is a str or a tuple
    of frozen models with only str/int/None fields - no plain list - so
    FilesystemUsageReport is unconditionally hashable.
    """
    assert isinstance(hash(_make_report()), int)
    assert isinstance(hash(FilesystemUsageReport(raw_text="")), int)


# ---------------------------------------------------------------------------
# FilesystemUsageReport: serialization / deserialization
# ---------------------------------------------------------------------------


def test_report_json_round_trip_uses_camel_case_aliases() -> None:
    report = _make_report()
    data = report.model_dump(mode="json", by_alias=True)

    assert "filesystems" in data
    assert data["rawText"] == report.raw_text
    assert data["rawStderr"] == report.raw_stderr
    assert "raw_text" not in data
    assert data["filesystems"][0]["fsType"] == "ext4"

    reloaded = FilesystemUsageReport.model_validate(data)
    assert reloaded == report


def test_report_json_round_trip_with_defaults() -> None:
    report = FilesystemUsageReport(raw_text="")
    data = report.model_dump(mode="json", by_alias=True)

    assert data["filesystems"] == []
    assert data["rawStderr"] == ""

    reloaded = FilesystemUsageReport.model_validate(data)
    assert reloaded == report


def test_report_json_round_trip_with_duplicate_targets() -> None:
    first = _make_usage(source="/dev/nvme0n1p2", target="/mnt/shared")
    second = _make_usage(source="tmpfs", target="/mnt/shared")
    report = FilesystemUsageReport(filesystems=(first, second), raw_text="...")

    data = report.model_dump(mode="json", by_alias=True)
    reloaded = FilesystemUsageReport.model_validate(data)

    assert len(reloaded.filesystems) == 2
    assert reloaded == report
