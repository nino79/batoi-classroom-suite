from __future__ import annotations

import pytest

import bcs.__main__ as main_module
from bcs.errors import ConfigInvalidError
from bcs.exit_codes import ExitCode


def test_bcs_error_maps_to_its_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_app(*_args: object, **_kwargs: object) -> None:
        raise ConfigInvalidError("bad config")

    monkeypatch.setattr(main_module, "app", _raise_app)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()
    assert exc_info.value.code == int(ExitCode.CONFIG_INVALID)


def test_keyboard_interrupt_maps_to_interrupted(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_app(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "app", _raise_app)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()
    assert exc_info.value.code == int(ExitCode.INTERRUPTED)


def test_unexpected_exception_maps_to_general_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_app(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("something broke")

    monkeypatch.setattr(main_module, "app", _raise_app)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()
    assert exc_info.value.code == int(ExitCode.GENERAL_ERROR)


def test_normal_system_exit_from_typer_propagates_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_app(*_args: object, **_kwargs: object) -> None:
        raise SystemExit(6)

    monkeypatch.setattr(main_module, "app", _raise_app)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()
    assert exc_info.value.code == 6
