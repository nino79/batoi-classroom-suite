from __future__ import annotations

import pytest

from bcs.argv_normalize import normalize_argv


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["version"], ["version"]),
        (["-o", "json", "version"], ["-o", "json", "version"]),
        (["version", "--output", "json"], ["--output", "json", "version"]),
        (["version", "-o", "json"], ["-o", "json", "version"]),
        (["doctor", "--strict"], ["doctor", "--strict"]),
        (
            ["validate", "file.yaml", "--strict", "-v"],
            ["-v", "validate", "file.yaml", "--strict"],
        ),
        (["-v", "validate", "file.yaml"], ["-v", "validate", "file.yaml"]),
        (["validate", "file.yaml", "-vv"], ["-vv", "validate", "file.yaml"]),
        (
            ["build", "--tag", "nightly", "--output", "json"],
            ["--output", "json", "build", "--tag", "nightly"],
        ),
    ],
)
def test_hoists_known_global_options_after_subcommand(argv: list[str], expected: list[str]) -> None:
    assert normalize_argv(argv) == expected


def test_leaves_argv_after_double_dash_untouched() -> None:
    argv = ["validate", "--", "--output", "not-an-option"]
    assert normalize_argv(argv) == argv


def test_option_at_end_with_no_value_left_in_place() -> None:
    # --config with no following token: nothing to hoist a value with,
    # left where Click can report a clear "missing value" error itself.
    argv = ["validate", "--config"]
    assert normalize_argv(argv) == ["validate", "--config"]


def test_inline_equals_value_form() -> None:
    assert normalize_argv(["version", "--output=json"]) == ["--output=json", "version"]


def test_empty_argv_is_returned_unchanged() -> None:
    assert normalize_argv([]) == []


def test_only_options_no_subcommand() -> None:
    assert normalize_argv(["--help"]) == ["--help"]


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["doctor", "--help"], ["doctor", "--help"]),
        (["doctor", "-h"], ["doctor", "-h"]),
        (["validate", "--version"], ["validate", "--version"]),
        (["-v", "doctor", "--help"], ["-v", "doctor", "--help"]),
        # -v is a genuine global option and is still hoisted; --help is not.
        (["doctor", "-v", "--help"], ["-v", "doctor", "--help"]),
    ],
)
def test_help_and_version_are_not_hoisted_past_the_subcommand(
    argv: list[str], expected: list[str]
) -> None:
    """``--help``/``-h``/``--version`` must stay wherever the caller put

    them relative to the subcommand - per docs/CLI.md#global-options,
    ``--help``/``-h`` shows help "for the current command" and
    ``--version`` is "not valid after a subcommand". Hoisting them (like
    genuine global options such as ``-v``) would make every
    ``bcs <command> --help`` show the top-level help instead of the
    command's own.
    """
    assert normalize_argv(argv) == expected
