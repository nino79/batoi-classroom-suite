from __future__ import annotations

import pytest

from bcs.commands.stubs import STUB_COMMANDS, NotImplementedInPhaseError, run_stub
from bcs.exit_codes import ExitCode


def test_documented_stub_commands_are_exactly_the_seven_deferred_ones() -> None:
    names = {s.name for s in STUB_COMMANDS}
    assert names == {"build", "install", "deploy", "backup", "restore", "update", "config"}


@pytest.mark.parametrize("stub", STUB_COMMANDS, ids=lambda s: s.name)
def test_every_stub_raises_not_implemented(make_runtime_context, stub) -> None:
    runtime = make_runtime_context()
    with pytest.raises(NotImplementedInPhaseError) as exc_info:
        run_stub(runtime, stub)
    assert exc_info.value.exit_code == ExitCode.GENERAL_ERROR
    assert stub.name in exc_info.value.message
    assert stub.owner in exc_info.value.message
