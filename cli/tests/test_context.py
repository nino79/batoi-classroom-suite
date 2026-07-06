from __future__ import annotations

import dataclasses

from bcs.context import RuntimeContext


def test_runtime_context_is_frozen(make_runtime_context) -> None:
    runtime = make_runtime_context()
    assert dataclasses.is_dataclass(runtime)
    try:
        runtime.no_input = True  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("RuntimeContext should be immutable")


def test_runtime_context_carries_all_collaborators(make_runtime_context) -> None:
    runtime = make_runtime_context()
    assert isinstance(runtime, RuntimeContext)
    assert runtime.config_loader is not None
    assert runtime.preferences is not None
    assert runtime.console is not None
    assert runtime.err_console is not None
    assert runtime.invocation_id
