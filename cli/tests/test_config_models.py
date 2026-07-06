from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from bcs.config.models import ClassroomConfig


def test_parses_real_example_config(real_example_config_path: Path) -> None:
    data = yaml.safe_load(real_example_config_path.read_text(encoding="utf-8"))
    config = ClassroomConfig.model_validate(data)
    assert config.metadata.name == "cipfp-batoi-aula-201"
    assert config.spec.project.centre == "CIPFP Batoi"
    assert [e.id for e in config.spec.boot_manager.menu.entries] == [
        "normal-boot",
        "maintenance",
    ]


def test_parses_minimal_valid_config(valid_config_data: dict[str, Any]) -> None:
    config = ClassroomConfig.model_validate(valid_config_data)
    assert config.api_version == "bcs/v1alpha1"
    assert config.spec.builder.partitioning.scheme == "gpt"
    assert config.spec.builder.partitioning.esp_size_mi_b == 512


def test_embed_shared_credentials_cannot_be_true(valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["security"] = {"credentials": {"embedSharedCredentials": True}}
    with pytest.raises(ValidationError):
        ClassroomConfig.model_validate(data)


def test_unknown_top_level_spec_field_is_rejected(valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["notARealField"] = "nope"
    with pytest.raises(ValidationError):
        ClassroomConfig.model_validate(data)


def test_x_prefixed_spec_field_is_allowed(valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["x-cipfp-note"] = "allowed"
    config = ClassroomConfig.model_validate(data)
    assert config.spec.model_extra == {"x-cipfp-note": "allowed"}


def test_bad_secure_boot_enum_is_rejected(valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["security"] = {"secureBoot": {"mode": "not-a-real-mode"}}
    with pytest.raises(ValidationError):
        ClassroomConfig.model_validate(data)


def test_missing_required_project_field_is_rejected(valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    del data["spec"]["project"]["centre"]
    with pytest.raises(ValidationError):
        ClassroomConfig.model_validate(data)


def test_metadata_name_pattern_rejects_uppercase() -> None:
    from bcs.config.models import Metadata

    with pytest.raises(ValidationError):
        Metadata.model_validate({"name": "Not-Valid-Slug"})


def test_hex_color_pattern(valid_config_data: dict[str, Any]) -> None:
    data = copy.deepcopy(valid_config_data)
    data["spec"]["branding"] = {"colors": {"primary": "not-a-hex-color"}}
    with pytest.raises(ValidationError):
        ClassroomConfig.model_validate(data)

    data["spec"]["branding"] = {"colors": {"primary": "#0057B8"}}
    config = ClassroomConfig.model_validate(data)
    assert config.spec.branding is not None
    assert config.spec.branding.colors is not None
    assert config.spec.branding.colors.primary == "#0057B8"
