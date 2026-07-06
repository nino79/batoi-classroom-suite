from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bcs.platform.errors import CommandExecutionError, CommandNotFoundError, CommandTimeoutError
from bcs.platform.execution import CommandRunner, SubprocessCommandRunner


def _completed(
    *, args: tuple[str, ...], returncode: int = 0, stdout: object = "", stderr: object = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args, returncode=returncode, stdout=stdout, stderr=stderr
    )


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_subprocess_command_runner_satisfies_command_runner_protocol() -> None:
    assert isinstance(SubprocessCommandRunner(), CommandRunner)


def test_any_object_with_a_matching_run_method_satisfies_the_protocol() -> None:
    class _Minimal:
        def run(self, command, **kwargs):  # type: ignore[no-untyped-def]
            raise NotImplementedError

    assert isinstance(_Minimal(), CommandRunner)


def test_object_without_run_method_does_not_satisfy_protocol() -> None:
    assert not isinstance(object(), CommandRunner)


# ---------------------------------------------------------------------------
# success path (mocked)
# ---------------------------------------------------------------------------


def test_successful_command_returns_populated_result(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = MagicMock(
        return_value=_completed(args=("efibootmgr", "-v"), returncode=0, stdout="ok\n", stderr="")
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = SubprocessCommandRunner()
    result = runner.run(["efibootmgr", "-v"])

    assert result.command == ("efibootmgr", "-v")
    assert result.stdout == "ok\n"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.success is True
    assert result.working_directory is None
    assert isinstance(result.started_at, datetime)
    assert isinstance(result.finished_at, datetime)
    assert result.finished_at >= result.started_at
    assert result.duration >= 0


def test_nonzero_exit_without_check_returns_result_not_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_run = MagicMock(return_value=_completed(args=("false",), returncode=1))
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = SubprocessCommandRunner().run(["false"])
    assert result.exit_code == 1
    assert result.success is False


def test_nonzero_exit_with_check_raises_command_execution_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_run = MagicMock(return_value=_completed(args=("false",), returncode=1, stderr="boom"))
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandExecutionError) as exc_info:
        SubprocessCommandRunner().run(["false"], check=True)
    assert exc_info.value.result.exit_code == 1
    assert exc_info.value.result.stderr == "boom"


def test_bytes_output_is_decoded_defensively(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive coverage: even if a CompletedProcess somehow carries
    bytes (subprocess itself never should, given text=True/encoding is
    always passed), decoding must not crash.
    """
    fake_run = MagicMock(
        return_value=_completed(args=("tool",), returncode=0, stdout=b"caf\xe9", stderr=b"")
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = SubprocessCommandRunner().run(["tool"])
    assert result.stdout == "caf�"


# ---------------------------------------------------------------------------
# CommandNotFoundError (mocked)
# ---------------------------------------------------------------------------


def test_missing_executable_raises_command_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_run = MagicMock(side_effect=FileNotFoundError("no such file"))
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandNotFoundError) as exc_info:
        SubprocessCommandRunner().run(["does-not-exist"])
    assert exc_info.value.executable == "does-not-exist"


def test_permission_error_raises_command_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_run = MagicMock(side_effect=PermissionError("not executable"))
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandNotFoundError) as exc_info:
        SubprocessCommandRunner().run(["/etc/not-executable"])
    assert exc_info.value.executable == "/etc/not-executable"


# ---------------------------------------------------------------------------
# CommandTimeoutError (mocked)
# ---------------------------------------------------------------------------


def test_timeout_raises_command_timeout_error_with_partial_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_run = MagicMock(
        side_effect=subprocess.TimeoutExpired(
            cmd=("sleep", "10"), timeout=5, output="partial stdout", stderr="partial stderr"
        )
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandTimeoutError) as exc_info:
        SubprocessCommandRunner().run(["sleep", "10"], timeout_seconds=5)

    partial = exc_info.value.partial_result
    assert partial.timed_out is True
    assert partial.exit_code is None
    assert partial.stdout == "partial stdout"
    assert partial.stderr == "partial stderr"
    assert partial.command == ("sleep", "10")


def test_timeout_with_no_captured_output_still_builds_valid_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_run = MagicMock(side_effect=subprocess.TimeoutExpired(cmd=("sleep", "10"), timeout=1))
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandTimeoutError) as exc_info:
        SubprocessCommandRunner().run(["sleep", "10"], timeout_seconds=1)
    assert exc_info.value.partial_result.stdout == ""
    assert exc_info.value.partial_result.stderr == ""


def test_timeout_with_bytes_output_is_decoded(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = MagicMock(
        side_effect=subprocess.TimeoutExpired(
            cmd=("sleep", "10"), timeout=1, output=b"partial", stderr=b""
        )
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandTimeoutError) as exc_info:
        SubprocessCommandRunner().run(["sleep", "10"], timeout_seconds=1)
    assert exc_info.value.partial_result.stdout == "partial"


# ---------------------------------------------------------------------------
# argument-list-only / shell=True never used / parameter passthrough
# ---------------------------------------------------------------------------


def test_empty_command_is_rejected_before_calling_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_run = MagicMock()
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ValueError, match="command must not be empty"):
        SubprocessCommandRunner().run([])
    fake_run.assert_not_called()


def test_shell_is_never_true(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = MagicMock(return_value=_completed(args=("true",)))
    monkeypatch.setattr(subprocess, "run", fake_run)

    SubprocessCommandRunner().run(["true"])
    assert fake_run.call_args.kwargs["shell"] is False


def test_command_passed_as_tuple_not_a_shell_string(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = MagicMock(return_value=_completed(args=("echo", "hi")))
    monkeypatch.setattr(subprocess, "run", fake_run)

    SubprocessCommandRunner().run(["echo", "hi"])
    called_command = fake_run.call_args.args[0]
    assert called_command == ("echo", "hi")
    assert isinstance(called_command, tuple)


def test_timeout_seconds_is_passed_through(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = MagicMock(return_value=_completed(args=("true",)))
    monkeypatch.setattr(subprocess, "run", fake_run)

    SubprocessCommandRunner().run(["true"], timeout_seconds=3.5)
    assert fake_run.call_args.kwargs["timeout"] == 3.5


def test_env_none_means_inherit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = MagicMock(return_value=_completed(args=("true",)))
    monkeypatch.setattr(subprocess, "run", fake_run)

    SubprocessCommandRunner().run(["true"])
    assert fake_run.call_args.kwargs["env"] is None


def test_env_replaces_not_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = MagicMock(return_value=_completed(args=("true",)))
    monkeypatch.setattr(subprocess, "run", fake_run)

    SubprocessCommandRunner().run(["true"], env={"FOO": "bar"})
    assert fake_run.call_args.kwargs["env"] == {"FOO": "bar"}


def test_cwd_is_passed_through_and_recorded_on_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_run = MagicMock(return_value=_completed(args=("true",)))
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = SubprocessCommandRunner().run(["true"], cwd=tmp_path)
    assert fake_run.call_args.kwargs["cwd"] == tmp_path
    assert result.working_directory == str(tmp_path)


def test_input_text_is_passed_through(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = MagicMock(return_value=_completed(args=("cat",)))
    monkeypatch.setattr(subprocess, "run", fake_run)

    SubprocessCommandRunner().run(["cat"], input_text="hello")
    assert fake_run.call_args.kwargs["input"] == "hello"


def test_capture_output_and_text_mode_are_always_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_run = MagicMock(return_value=_completed(args=("true",)))
    monkeypatch.setattr(subprocess, "run", fake_run)

    SubprocessCommandRunner().run(["true"])
    kwargs = fake_run.call_args.kwargs
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False


# ---------------------------------------------------------------------------
# real, end-to-end tests - cross-platform via sys.executable, per
# docs/PLATFORM_LAYER.md's own testing strategy (not mocked)
# ---------------------------------------------------------------------------


def test_real_success_captures_stdout() -> None:
    result = SubprocessCommandRunner().run([sys.executable, "-c", "print('hello')"])
    assert result.stdout.strip() == "hello"
    assert result.success is True


def test_real_nonzero_exit() -> None:
    result = SubprocessCommandRunner().run([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert result.exit_code == 3
    assert result.success is False


def test_real_timeout_raises() -> None:
    with pytest.raises(CommandTimeoutError):
        SubprocessCommandRunner().run(
            [sys.executable, "-c", "import time; time.sleep(5)"], timeout_seconds=0.2
        )


def test_real_missing_executable_raises() -> None:
    with pytest.raises(CommandNotFoundError):
        SubprocessCommandRunner().run(["bcs-this-executable-does-not-exist-anywhere"])
