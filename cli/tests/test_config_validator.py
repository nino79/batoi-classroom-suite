from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from bcs.config.loader import ConfigLoader
from bcs.config.validator import validate_document


def _write(tmp_path: Path, data: dict[str, Any], name: str = "config.yaml") -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_valid_document_has_no_errors_or_warnings(
    tmp_path: Path, valid_config_data: dict[str, Any]
) -> None:
    path = _write(tmp_path, valid_config_data)
    loader = ConfigLoader(explicit_path=path, env={})
    report = validate_document(loader, path)
    assert report.valid
    assert not report.errors
    assert not report.warnings


def test_label_locale_coverage_rule(tmp_path: Path, valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["bootManager"]["menu"]["entries"][0]["label"]["fr_FR"] = "Demarrer"
    path = _write(tmp_path, data)
    loader = ConfigLoader(explicit_path=path, env={})
    report = validate_document(loader, path)
    assert not report.valid
    assert any(e.rule == "label-locale-coverage" for e in report.errors)


def test_default_entry_exists_rule(tmp_path: Path, valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["bootManager"]["menu"]["defaultEntry"] = "does-not-exist"
    path = _write(tmp_path, data)
    loader = ConfigLoader(explicit_path=path, env={})
    report = validate_document(loader, path)
    assert not report.valid
    assert any(e.rule == "default-entry-exists" for e in report.errors)


def test_checksum_algorithm_mismatch_is_a_warning(
    tmp_path: Path, valid_config_data: dict[str, Any]
) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["builder"]["provenance"] = {"checksumAlgorithm": "sha256"}
    data["spec"]["deploy"] = {"verification": {"checksumAlgorithm": "sha512"}}
    path = _write(tmp_path, data)
    loader = ConfigLoader(explicit_path=path, env={})
    report = validate_document(loader, path)
    assert report.valid  # warnings alone do not fail validation
    assert any(w.rule == "checksum-algorithm-match" for w in report.warnings)


def test_static_assignments_present_rule(tmp_path: Path, valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["network"]["addressing"] = {"mode": "static"}
    path = _write(tmp_path, data)
    loader = ConfigLoader(explicit_path=path, env={})
    report = validate_document(loader, path)
    assert any(w.rule == "static-assignments-present" for w in report.warnings)


def test_strict_mode_treats_warnings_as_failing(
    tmp_path: Path, valid_config_data: dict[str, Any]
) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["network"]["addressing"] = {"mode": "static"}
    path = _write(tmp_path, data)
    loader = ConfigLoader(explicit_path=path, env={})
    report = validate_document(loader, path)
    assert report.is_ok(strict=False) is True
    assert report.is_ok(strict=True) is False


def test_schema_errors_reported_without_raising(
    tmp_path: Path, valid_config_data: dict[str, Any]
) -> None:
    data = copy.deepcopy(valid_config_data)
    del data["spec"]["packages"]
    path = _write(tmp_path, data)
    loader = ConfigLoader(explicit_path=path, env={})
    report = validate_document(loader, path)
    assert not report.valid
    assert report.errors


def test_report_as_dict_shape(tmp_path: Path, valid_config_data: dict[str, Any]) -> None:
    path = _write(tmp_path, valid_config_data)
    loader = ConfigLoader(explicit_path=path, env={})
    report = validate_document(loader, path)
    payload = report.as_dict()
    assert set(payload) == {"valid", "errors", "warnings"}
