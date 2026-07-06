from __future__ import annotations

import io
import json

from bcs.logging_setup import (
    LogFormat,
    LogLevel,
    LogLevelOption,
    configure_logging,
    get_logger,
    resolve_log_level,
)


def test_explicit_log_level_wins_over_verbose_and_quiet() -> None:
    level = resolve_log_level(explicit=LogLevel.TRACE, verbose_count=0, quiet=True)
    assert level is LogLevel.TRACE


def test_default_is_info() -> None:
    assert resolve_log_level(explicit=None, verbose_count=0, quiet=False) is LogLevel.INFO


def test_verbose_steps_towards_trace() -> None:
    assert resolve_log_level(explicit=None, verbose_count=1, quiet=False) is LogLevel.DEBUG
    assert resolve_log_level(explicit=None, verbose_count=2, quiet=False) is LogLevel.TRACE
    # -vvv (3+) clamps at TRACE - no lower level exists.
    assert resolve_log_level(explicit=None, verbose_count=5, quiet=False) is LogLevel.TRACE


def test_quiet_drops_to_error() -> None:
    assert resolve_log_level(explicit=None, verbose_count=0, quiet=True) is LogLevel.ERROR


def test_verbose_and_quiet_conflict_favors_verbose_and_warns() -> None:
    warn_stream = io.StringIO()
    level = resolve_log_level(explicit=None, verbose_count=1, quiet=True, warn=warn_stream)
    assert level is LogLevel.DEBUG
    assert "both --verbose and --quiet" in warn_stream.getvalue()


def test_log_level_option_maps_to_log_level() -> None:
    assert LogLevelOption.SILENT.to_log_level() is LogLevel.SILENT
    assert LogLevelOption.TRACE.to_log_level() is LogLevel.TRACE


def test_text_format_contains_invocation_id_and_level() -> None:
    stream = io.StringIO()
    logger = configure_logging(
        level=LogLevel.INFO,
        log_format=LogFormat.TEXT,
        invocation_id="01TESTINVOCATIONID0000000",
        command="doctor",
        stream=stream,
    )
    logger.info("hello world")
    output = stream.getvalue()
    assert "01TESTINVOCATIONID0000000" in output
    assert "INFO" in output
    assert "hello world" in output


def test_json_format_is_one_object_per_line() -> None:
    stream = io.StringIO()
    logger = configure_logging(
        level=LogLevel.INFO,
        log_format=LogFormat.JSON,
        invocation_id="01TESTINVOCATIONID0000000",
        command="doctor",
        stream=stream,
    )
    logger.info("hello json")
    payload = json.loads(stream.getvalue().strip())
    assert payload["invocationId"] == "01TESTINVOCATIONID0000000"
    assert payload["level"] == "info"
    assert payload["command"] == "doctor"
    assert payload["message"] == "hello json"


def test_secrets_are_redacted() -> None:
    stream = io.StringIO()
    logger = configure_logging(
        level=LogLevel.DEBUG,
        log_format=LogFormat.TEXT,
        invocation_id="01TESTINVOCATIONID0000000",
        command="doctor",
        stream=stream,
    )
    logger.debug("resolved field spec.security.somePassword=hunter2")
    assert "hunter2" not in stream.getvalue()
    assert "***" in stream.getvalue()


def test_signing_key_is_not_redacted() -> None:
    stream = io.StringIO()
    logger = configure_logging(
        level=LogLevel.DEBUG,
        log_format=LogFormat.TEXT,
        invocation_id="01TESTINVOCATIONID0000000",
        command="doctor",
        stream=stream,
    )
    logger.debug("resolved field spec.packages.repositories.0.signingKey=keys/lliurex.gpg")
    assert "keys/lliurex.gpg" in stream.getvalue()


def test_configure_logging_is_idempotent_per_process() -> None:
    stream_a = io.StringIO()
    stream_b = io.StringIO()
    configure_logging(
        level=LogLevel.INFO,
        log_format=LogFormat.TEXT,
        invocation_id="a",
        command="x",
        stream=stream_a,
    )
    configure_logging(
        level=LogLevel.INFO,
        log_format=LogFormat.TEXT,
        invocation_id="b",
        command="y",
        stream=stream_b,
    )
    get_logger().info("only stream_b should get this")
    assert "only stream_b should get this" not in stream_a.getvalue()
    assert "only stream_b should get this" in stream_b.getvalue()
