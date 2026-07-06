from __future__ import annotations

import pytest

from bcs.errors import (
    AbortedError,
    BcsError,
    BcsTimeoutError,
    ConfigInvalidError,
    PartialFailureError,
    PluginError,
    PreconditionFailedError,
    UsageError,
)
from bcs.exit_codes import ExitCode


@pytest.mark.parametrize(
    ("error_cls", "expected_code"),
    [
        (UsageError, ExitCode.USAGE_ERROR),
        (ConfigInvalidError, ExitCode.CONFIG_INVALID),
        (PreconditionFailedError, ExitCode.PRECONDITION_FAILED),
        (AbortedError, ExitCode.ABORTED),
        (PartialFailureError, ExitCode.PARTIAL_FAILURE),
        (BcsTimeoutError, ExitCode.TIMEOUT),
        (PluginError, ExitCode.PLUGIN_ERROR),
    ],
)
def test_error_exit_codes(error_cls: type[BcsError], expected_code: ExitCode) -> None:
    err = error_cls("boom")
    assert err.exit_code == expected_code
    assert err.message == "boom"
    assert isinstance(err, BcsError)


def test_config_invalid_error_carries_error_list() -> None:
    err = ConfigInvalidError("bad config", errors=["a", "b"])
    assert err.errors == ["a", "b"]


def test_config_invalid_error_defaults_to_empty_list() -> None:
    err = ConfigInvalidError("bad config")
    assert err.errors == []
