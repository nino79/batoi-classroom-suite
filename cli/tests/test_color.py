from __future__ import annotations

import io

import pytest

from bcs.color import ColorMode, resolve_color_enabled
from bcs.output import OutputFormat


class _FakeStream(io.StringIO):
    def __init__(self, is_a_tty: bool) -> None:
        super().__init__()
        self._is_a_tty = is_a_tty

    def isatty(self) -> bool:
        return self._is_a_tty


@pytest.mark.parametrize("tty", [True, False])
def test_never_colorizes_non_text_output(tty: bool) -> None:
    stream = _FakeStream(tty)
    assert (
        resolve_color_enabled(
            mode=ColorMode.ALWAYS, output_format=OutputFormat.JSON, stream=stream, env={}
        )
        is False
    )


def test_always_forces_color_for_text() -> None:
    stream = _FakeStream(False)
    assert (
        resolve_color_enabled(
            mode=ColorMode.ALWAYS, output_format=OutputFormat.TEXT, stream=stream, env={}
        )
        is True
    )


def test_never_disables_color_for_text() -> None:
    stream = _FakeStream(True)
    assert (
        resolve_color_enabled(
            mode=ColorMode.NEVER, output_format=OutputFormat.TEXT, stream=stream, env={}
        )
        is False
    )


def test_auto_follows_tty_by_default() -> None:
    assert (
        resolve_color_enabled(
            mode=ColorMode.AUTO, output_format=OutputFormat.TEXT, stream=_FakeStream(True), env={}
        )
        is True
    )
    assert (
        resolve_color_enabled(
            mode=ColorMode.AUTO, output_format=OutputFormat.TEXT, stream=_FakeStream(False), env={}
        )
        is False
    )


def test_no_color_env_disables_auto() -> None:
    assert (
        resolve_color_enabled(
            mode=ColorMode.AUTO,
            output_format=OutputFormat.TEXT,
            stream=_FakeStream(True),
            env={"NO_COLOR": "1"},
        )
        is False
    )


def test_bcs_color_env_takes_precedence_over_no_color() -> None:
    assert (
        resolve_color_enabled(
            mode=ColorMode.AUTO,
            output_format=OutputFormat.TEXT,
            stream=_FakeStream(True),
            env={"NO_COLOR": "1", "BCS_COLOR": "always"},
        )
        is True
    )


def test_dumb_term_disables_auto() -> None:
    assert (
        resolve_color_enabled(
            mode=ColorMode.AUTO,
            output_format=OutputFormat.TEXT,
            stream=_FakeStream(True),
            env={"TERM": "dumb"},
        )
        is False
    )


def test_flag_precedence_over_env() -> None:
    """--color flag beats BCS_COLOR/NO_COLOR entirely."""
    assert (
        resolve_color_enabled(
            mode=ColorMode.NEVER,
            output_format=OutputFormat.TEXT,
            stream=_FakeStream(True),
            env={"BCS_COLOR": "always"},
        )
        is False
    )
