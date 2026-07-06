from __future__ import annotations

from pathlib import Path

import pytest

from bcs.config.loader import ConfigLoader
from bcs.errors import ConfigInvalidError, UsageError


def test_explicit_path_wins(valid_config_path: Path, tmp_path: Path) -> None:
    loader = ConfigLoader(explicit_path=valid_config_path, env={})
    assert loader.resolve_path() == valid_config_path


def test_explicit_path_must_exist(tmp_path: Path) -> None:
    loader = ConfigLoader(explicit_path=tmp_path / "missing.yaml", env={})
    with pytest.raises(UsageError):
        loader.resolve_path()


def test_env_var_used_when_no_explicit_path(valid_config_path: Path) -> None:
    loader = ConfigLoader(explicit_path=None, env={"BCS_CONFIG": str(valid_config_path)})
    assert loader.resolve_path() == valid_config_path


def test_explicit_path_beats_env_var(valid_config_path: Path, tmp_path: Path) -> None:
    other = tmp_path / "other.yaml"
    other.write_text(valid_config_path.read_text(encoding="utf-8"), encoding="utf-8")
    loader = ConfigLoader(explicit_path=valid_config_path, env={"BCS_CONFIG": str(other)})
    assert loader.resolve_path() == valid_config_path


def test_default_candidate_in_cwd(tmp_path: Path, valid_config_path: Path) -> None:
    classroom_dir = tmp_path / "classroom-dir"
    classroom_dir.mkdir()
    target = classroom_dir / "bcs.yaml"
    target.write_text(valid_config_path.read_text(encoding="utf-8"), encoding="utf-8")
    loader = ConfigLoader(explicit_path=None, env={}, cwd=classroom_dir)
    assert loader.resolve_path() == target


def test_ambiguous_default_candidates_raise(tmp_path: Path, valid_config_path: Path) -> None:
    text = valid_config_path.read_text(encoding="utf-8")
    (tmp_path / "bcs.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "classroom.yaml").write_text(text, encoding="utf-8")
    loader = ConfigLoader(explicit_path=None, env={}, cwd=tmp_path)
    with pytest.raises(UsageError, match="ambiguous"):
        loader.resolve_path()


def test_no_config_found_raises_usage_error(tmp_path: Path) -> None:
    loader = ConfigLoader(explicit_path=None, env={}, cwd=tmp_path)
    with pytest.raises(UsageError, match="no ClassroomConfig found"):
        loader.resolve_path()


def test_no_upward_directory_search(tmp_path: Path, valid_config_path: Path) -> None:
    """A parent directory's bcs.yaml must NOT be found from a subdirectory."""
    (tmp_path / "bcs.yaml").write_text(
        valid_config_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    loader = ConfigLoader(explicit_path=None, env={}, cwd=subdir)
    with pytest.raises(UsageError, match="no ClassroomConfig found"):
        loader.resolve_path()


def test_load_returns_validated_config(valid_config_path: Path) -> None:
    loader = ConfigLoader(explicit_path=valid_config_path, env={})
    config = loader.load()
    assert config.metadata.name == "test-classroom"


def test_load_applies_set_overrides(valid_config_path: Path) -> None:
    loader = ConfigLoader(
        explicit_path=valid_config_path,
        set_overrides=["spec.security.secureBoot.mode=disabled"],
        env={},
    )
    config = loader.load()
    assert config.spec.security.secure_boot.mode == "disabled"


def test_load_applies_env_overrides(valid_config_path: Path) -> None:
    loader = ConfigLoader(
        explicit_path=valid_config_path,
        env={"BCS_CFG_SPEC_SECURITY_SECUREBOOT_MODE": "permissive"},
    )
    config = loader.load()
    assert config.spec.security.secure_boot.mode == "permissive"


def test_set_overrides_beat_env_overrides(valid_config_path: Path) -> None:
    loader = ConfigLoader(
        explicit_path=valid_config_path,
        set_overrides=["spec.security.secureBoot.mode=enforce"],
        env={"BCS_CFG_SPEC_SECURITY_SECUREBOOT_MODE": "disabled"},
    )
    config = loader.load()
    assert config.spec.security.secure_boot.mode == "enforce"


def test_invalid_yaml_syntax_raises_config_invalid(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("apiVersion: bcs/v1alpha1\nkind: [unterminated", encoding="utf-8")
    loader = ConfigLoader(explicit_path=bad, env={})
    with pytest.raises(ConfigInvalidError):
        loader.load()


def test_unrecognized_api_version_raises_config_invalid(
    tmp_path: Path, valid_config_data: dict
) -> None:
    import yaml

    data = dict(valid_config_data)
    data["apiVersion"] = "bcs/v99"
    path = tmp_path / "future.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    loader = ConfigLoader(explicit_path=path, env={})
    with pytest.raises(ConfigInvalidError, match="apiVersion"):
        loader.load()


def test_unrecognized_kind_raises_config_invalid(tmp_path: Path, valid_config_data: dict) -> None:
    import yaml

    data = dict(valid_config_data)
    data["kind"] = "FleetConfig"
    path = tmp_path / "fleet.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    loader = ConfigLoader(explicit_path=path, env={})
    with pytest.raises(ConfigInvalidError, match="kind"):
        loader.load()


def test_schema_violation_raises_config_invalid_with_errors(
    tmp_path: Path, valid_config_data: dict
) -> None:
    import yaml

    data = dict(valid_config_data)
    del data["spec"]["packages"]
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    loader = ConfigLoader(explicit_path=path, env={})
    with pytest.raises(ConfigInvalidError) as exc_info:
        loader.load()
    assert exc_info.value.errors
