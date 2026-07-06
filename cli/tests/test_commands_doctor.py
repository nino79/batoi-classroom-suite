from __future__ import annotations

from pathlib import Path

import pytest

from bcs.commands import doctor as doctor_module
from bcs.commands.doctor import run_doctor
from bcs.errors import PreconditionFailedError, UsageError
from bcs.inventory.models import (
    EfiSystemPartition,
    FirmwareInfo,
    NetworkInterface,
    SecureBootState,
    StorageDevice,
    ToolStatus,
    UsbStorageDevice,
)
from bcs.output import OutputFormat

# ---------------------------------------------------------------------------
# Individual check-evaluation logic, exercised directly against a
# monkeypatched Host Inventory collector - these are the tests that were
# missing before doctor.py was refactored to build on bcs.inventory:
# every other test in this file monkeypatches the whole _ALL_CHECKS
# registry and never runs the real evaluation logic below.
# ---------------------------------------------------------------------------


def test_check_firmware_ok_when_uefi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.ENABLED),
    )
    result = doctor_module._check_firmware()
    assert result.status == "ok"


def test_check_firmware_fail_when_not_uefi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=False, secureBoot=SecureBootState.UNSUPPORTED),
    )
    result = doctor_module._check_firmware()
    assert result.status == "fail"


@pytest.mark.parametrize(
    ("state", "expected_status"),
    [
        (SecureBootState.UNSUPPORTED, "skip"),
        (SecureBootState.UNKNOWN, "warn"),
        (SecureBootState.ENABLED, "ok"),
        (SecureBootState.DISABLED, "warn"),
    ],
)
def test_check_secure_boot_maps_every_state(
    monkeypatch: pytest.MonkeyPatch, state: SecureBootState, expected_status: str
) -> None:
    monkeypatch.setattr(
        doctor_module, "collect_firmware", lambda: FirmwareInfo(uefi=True, secureBoot=state)
    )
    result = doctor_module._check_secure_boot()
    assert result.status == expected_status


def test_check_storage_ok_when_nvme_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_storage",
        lambda: [StorageDevice(name="nvme0n1", path="/dev/nvme0n1", isNvme=True)],
    )
    result = doctor_module._check_storage()
    assert result.status == "ok"
    assert "nvme0n1" in result.message


def test_check_storage_fail_when_none_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor_module, "collect_storage", list)
    result = doctor_module._check_storage()
    assert result.status == "fail"


def test_check_esp_fail_when_not_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_efi_system_partition",
        lambda: EfiSystemPartition(present=False, mounted=False),
    )
    result = doctor_module._check_esp()
    assert result.status == "fail"


def test_check_esp_warn_when_present_but_not_mounted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_efi_system_partition",
        lambda: EfiSystemPartition(present=True, mounted=False),
    )
    result = doctor_module._check_esp()
    assert result.status == "warn"


def test_check_esp_ok_when_mounted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_efi_system_partition",
        lambda: EfiSystemPartition(present=True, mountPoint="/boot/efi", mounted=True),
    )
    result = doctor_module._check_esp()
    assert result.status == "ok"
    assert "/boot/efi" in result.message


def test_check_usb_storage_skip_when_none_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor_module, "collect_usb_storage", list)
    result = doctor_module._check_usb_storage()
    assert result.status == "skip"


def test_check_usb_storage_ok_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_usb_storage",
        lambda: [UsbStorageDevice(name="sdb", path="/dev/sdb", mounted=False)],
    )
    result = doctor_module._check_usb_storage()
    assert result.status == "ok"
    assert "sdb" in result.message


def test_check_network_skip_when_only_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_network",
        lambda: [NetworkInterface(name="lo", isUp=True, isLoopback=True)],
    )
    result = doctor_module._check_network()
    assert result.status == "skip"


def test_check_network_ok_when_interface_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_network",
        lambda: [NetworkInterface(name="eth0", isUp=True, isLoopback=False)],
    )
    result = doctor_module._check_network()
    assert result.status == "ok"


def test_check_network_warn_when_interface_present_but_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_network",
        lambda: [NetworkInterface(name="eth0", isUp=False, isLoopback=False)],
    )
    result = doctor_module._check_network()
    assert result.status == "warn"


def test_check_tooling_ok_when_all_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_tooling",
        lambda: [ToolStatus(name="clonezilla", found=True, path="/usr/bin/clonezilla")],
    )
    result = doctor_module._check_tooling()
    assert result.status == "ok"


def test_check_tooling_fail_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_tooling",
        lambda: [ToolStatus(name="clonezilla", found=False, path=None)],
    )
    result = doctor_module._check_tooling()
    assert result.status == "fail"
    assert "clonezilla" in result.message


def test_unknown_check_name_raises_usage_error(make_runtime_context) -> None:
    runtime = make_runtime_context()
    with pytest.raises(UsageError):
        run_doctor(runtime, checks=["not-a-real-check"])


def test_all_checks_ok_returns_zero(make_runtime_context, monkeypatch: pytest.MonkeyPatch) -> None:
    def _always_ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "all good")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _always_ok)

    runtime = make_runtime_context()
    assert run_doctor(runtime) == 0


def test_any_failing_check_raises_precondition_failed(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "fine")

    def _fail(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "fail", "broken")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _ok)
    monkeypatch.setitem(doctor_module._ALL_CHECKS, "tooling", _fail)

    runtime = make_runtime_context()
    with pytest.raises(PreconditionFailedError):
        run_doctor(runtime)


def test_warnings_alone_do_not_fail_without_strict(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "fine")

    def _warn(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "warn", "hmm")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _ok)
    monkeypatch.setitem(doctor_module._ALL_CHECKS, "permissions", _warn)

    runtime = make_runtime_context()
    assert run_doctor(runtime) == 0
    with pytest.raises(PreconditionFailedError):
        run_doctor(runtime, strict=True)


def test_json_output_shape(make_runtime_context, monkeypatch: pytest.MonkeyPatch) -> None:
    def _ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "fine")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _ok)

    runtime = make_runtime_context(output=OutputFormat.JSON)
    run_doctor(runtime)
    import json

    payload = json.loads(runtime.console.file.getvalue())
    assert payload["schemaVersion"] == "bcs-cli/v1alpha1"
    assert payload["summary"]["ok"] == len(doctor_module._ALL_CHECKS)


def test_config_check_warns_when_no_config_resolved(make_runtime_context) -> None:
    runtime = make_runtime_context()
    result = doctor_module._check_config(runtime)
    assert result.status == "warn"


def test_config_check_ok_for_valid_config(make_runtime_context, valid_config_path: Path) -> None:
    runtime = make_runtime_context(config_path=valid_config_path)
    result = doctor_module._check_config(runtime)
    assert result.status == "ok"


def test_selected_checks_limits_which_run(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def _tracker(name: str):
        def _inner(_runtime: object) -> doctor_module.CheckResult:
            calls.append(name)
            return doctor_module.CheckResult(name, "ok", "fine")

        return _inner

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _tracker(name))

    runtime = make_runtime_context()
    run_doctor(runtime, checks=["firmware", "storage"])
    assert calls == ["firmware", "storage"]
