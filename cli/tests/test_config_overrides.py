from __future__ import annotations

import pytest

from bcs.config.overrides import (
    apply_env_overrides,
    apply_set_overrides,
    get_by_path,
    parse_set_option,
    set_by_path,
)
from bcs.errors import UsageError


def test_get_by_path_nested() -> None:
    doc = {"spec": {"security": {"secureBoot": {"mode": "enforce"}}}}
    assert get_by_path(doc, "spec.security.secureBoot.mode") == "enforce"


def test_get_by_path_array_index() -> None:
    doc = {"spec": {"bootManager": {"menu": {"entries": [{"id": "a"}, {"id": "b"}]}}}}
    assert get_by_path(doc, "spec.bootManager.menu.entries.1.id") == "b"


def test_get_by_path_missing_field_raises_usage_error() -> None:
    with pytest.raises(UsageError):
        get_by_path({"spec": {}}, "spec.doesNotExist")


def test_set_by_path_creates_intermediate_mappings() -> None:
    doc: dict[str, object] = {}
    set_by_path(doc, "spec.security.secureBoot.mode", "disabled")
    assert doc == {"spec": {"security": {"secureBoot": {"mode": "disabled"}}}}


def test_parse_set_option() -> None:
    assert parse_set_option("spec.deploy.session.timeoutMinutes=90") == (
        "spec.deploy.session.timeoutMinutes",
        90,
    )
    assert parse_set_option("spec.security.credentials.embedSharedCredentials=false") == (
        "spec.security.credentials.embedSharedCredentials",
        False,
    )


def test_parse_set_option_requires_equals() -> None:
    with pytest.raises(UsageError):
        parse_set_option("no-equals-here")


def test_apply_set_overrides_applies_in_order() -> None:
    doc: dict[str, object] = {"spec": {"a": 1}}
    apply_set_overrides(doc, ["spec.a=2", "spec.a=3"])
    assert doc["spec"]["a"] == 3  # type: ignore[index]


def test_apply_env_overrides_case_corrects_camelcase_keys() -> None:
    doc = {"spec": {"security": {"secureBoot": {"mode": "enforce"}}}}
    apply_env_overrides(doc, {"BCS_CFG_SPEC_SECURITY_SECUREBOOT_MODE": "disabled"})
    assert doc["spec"]["security"]["secureBoot"]["mode"] == "disabled"  # type: ignore[index]


def test_apply_env_overrides_ignores_unrelated_vars() -> None:
    doc = {"spec": {"a": 1}}
    apply_env_overrides(doc, {"PATH": "/usr/bin", "HOME": "/home/x"})
    assert doc == {"spec": {"a": 1}}


def test_coercion_of_booleans_and_numbers() -> None:
    doc: dict[str, object] = {}
    apply_set_overrides(
        doc,
        [
            "a.bool_true=true",
            "a.bool_false=false",
            "a.int=42",
            "a.float=3.14",
            "a.string=hello",
            "a.null=null",
        ],
    )
    a = doc["a"]  # type: ignore[assignment]
    assert a["bool_true"] is True  # type: ignore[index]
    assert a["bool_false"] is False  # type: ignore[index]
    assert a["int"] == 42  # type: ignore[index]
    assert a["float"] == pytest.approx(3.14)  # type: ignore[index]
    assert a["string"] == "hello"  # type: ignore[index]
    assert a["null"] is None  # type: ignore[index]
