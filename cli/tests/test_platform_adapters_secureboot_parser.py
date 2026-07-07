"""Tests for the pure Secure Boot parser.

Per the fixture corpus's own placeholder rules
(``tests/fixtures/README.md``), the real corpus
(``tests/fixtures/secureboot/``) currently holds no scenario files at
all - the Secure Boot Adapter's design was only just accepted and its
fixtures-strategy follow-up (populating that directory) has not
happened yet. These tests therefore build a *temporary*,
``tmp_path``-rooted corpus (mirroring ``tests/fixtures/``'s own
layout) and load every scenario through ``fixture_utils.py``, exactly
as real captures will be loaded once they exist - never by passing an
inline string straight to the parser. The real corpus is never written
to.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bcs.platform.adapters.secureboot.models import SecureBootState
from bcs.platform.adapters.secureboot.parser import parse_secure_boot_status
from fixture_utils import load_fixture

_VALID_FIXTURES: dict[str, str] = {
    "mokutil_test_ubuntu-24.04_enabled.txt": "SecureBoot enabled\nSetupMode disabled\n",
    "mokutil_test_ubuntu-24.04_disabled.txt": "SecureBoot disabled\n",
    "mokutil_test_ubuntu-24.04_setup-mode.txt": "SecureBoot enabled\nSetupMode enabled\n",
    "mokutil_test_ubuntu-24.04_no-setup-mode-line.txt": "SecureBoot enabled\n",
    "mokutil_test_ubuntu-24.04_no-recognized-lines.txt": (
        "This file contains no mokutil-shaped lines at all.\nJust prose.\n"
    ),
    "mokutil_test_ubuntu-24.04_unknown-lines.txt": (
        "SecureBoot enabled\n"
        "SomeFutureField: something this parser does not know about\n"
        "SetupMode disabled\n"
        "# not a real mokutil line\n"
    ),
    "mokutil_test_ubuntu-24.04_blank-lines-and-whitespace.txt": (
        "\nSecureBoot   enabled\n\nSetupMode\tdisabled\n\n"
    ),
    "mokutil_test_ubuntu-24.04_crlf-line-endings.txt": (
        "SecureBoot enabled\r\nSetupMode disabled\r\n"
    ),
    "mokutil_test_ubuntu-24.04_last-value-wins.txt": (
        "SecureBoot enabled\nSecureBoot disabled\nSetupMode enabled\nSetupMode disabled\n"
    ),
}

_INVALID_FIXTURES: dict[str, str] = {
    "mokutil_test_ubuntu-24.04_malformed-secure-boot.txt": "SecureBoot maybe\n",
    "mokutil_test_ubuntu-24.04_malformed-setup-mode.txt": "SecureBoot enabled\nSetupMode maybe\n",
}


@pytest.fixture
def synthetic_corpus(tmp_path: Path) -> Path:
    """A temporary corpus, mirroring tests/fixtures/'s own layout, holding
    synthetic-but-realistic scenarios for parser correctness only. Never
    writes to the real corpus.
    """
    valid_dir = tmp_path / "secureboot" / "generic"
    invalid_dir = tmp_path / "secureboot" / "generic-invalid"
    valid_dir.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)
    for name, content in _VALID_FIXTURES.items():
        (valid_dir / name).write_text(content, encoding="utf-8")
    for name, content in _INVALID_FIXTURES.items():
        (invalid_dir / name).write_text(content, encoding="utf-8")
    return tmp_path


def _load(root: Path, name: str, *, invalid: bool = False) -> str:
    category = "generic-invalid" if invalid else "generic"
    return load_fixture("secureboot", category, name, root=root)


# ---------------------------------------------------------------------------
# well-formed scenarios
# ---------------------------------------------------------------------------


def test_enabled(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_enabled.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is False
    assert status.raw_text == text


def test_disabled(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_disabled.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.DISABLED
    assert status.setup_mode is None
    assert status.raw_text == text


def test_setup_mode_enabled(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_setup-mode.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is True


def test_no_setup_mode_line_leaves_it_none(synthetic_corpus: Path) -> None:
    """Some mokutil versions/builds don't report Setup Mode at all - this is
    expected, not an error, per docs/SECURE_BOOT_ADAPTER.md.
    """
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_no-setup-mode-line.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is None


def test_no_recognized_lines_yields_unknown_state(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_no-recognized-lines.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.UNKNOWN
    assert status.setup_mode is None
    assert status.raw_text == text


def test_unrecognized_lines_are_ignored_not_fatal(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_unknown-lines.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is False


def test_blank_lines_and_internal_whitespace_are_tolerated(synthetic_corpus: Path) -> None:
    """A blank line between recognized lines does not disrupt parsing, and
    extra internal whitespace (multiple spaces, a tab) between the field
    name and its value is tolerated.
    """
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_blank-lines-and-whitespace.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is False


def test_crlf_line_endings_are_handled(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_crlf-line-endings.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.ENABLED
    assert status.setup_mode is False


def test_later_line_wins_over_earlier_duplicate(synthetic_corpus: Path) -> None:
    """No documented behaviour forbids a duplicate SecureBoot/SetupMode
    line; the last one encountered simply wins, matching the same
    left-to-right overwrite semantics FirmwareBootConfiguration's own
    scalar fields (BootCurrent, Timeout, BootNext) already have.
    """
    text = _load(synthetic_corpus, "mokutil_test_ubuntu-24.04_last-value-wins.txt")
    status = parse_secure_boot_status(text)

    assert status.state == SecureBootState.DISABLED
    assert status.setup_mode is False


def test_empty_input_yields_unknown_state_and_no_setup_mode() -> None:
    """A genuinely empty string is a degenerate case the fixture corpus's
    own placeholder convention can't represent (a zero-byte file already
    means 'not yet captured'), so this is the one scenario tested inline
    rather than through the synthetic corpus.
    """
    status = parse_secure_boot_status("")

    assert status.state == SecureBootState.UNKNOWN
    assert status.setup_mode is None
    assert status.raw_text == ""


@pytest.mark.parametrize("name", sorted(_VALID_FIXTURES))
def test_every_valid_fixture_parses_without_error(synthetic_corpus: Path, name: str) -> None:
    text = _load(synthetic_corpus, name)
    status = parse_secure_boot_status(text)
    assert status.raw_text == text


def test_parser_never_produces_unsupported_state() -> None:
    """UNSUPPORTED is a valid SecureBootState value (see models.py), but
    this parser has no recognized text pattern that produces it - per
    docs/SECURE_BOOT_ADAPTER.md#parser-strategy and #error-mapping, that
    state is reserved for the future adapter layer (an EFI-variables-
    unavailable condition detected from a non-zero exit/stderr, never
    from stdout text). No input to this function can ever yield
    state=UNSUPPORTED.
    """
    for text in (*_VALID_FIXTURES.values(), "", "garbage\n"):
        assert parse_secure_boot_status(text).state != SecureBootState.UNSUPPORTED


# ---------------------------------------------------------------------------
# malformed mandatory fields - rejected, not silently ignored
# ---------------------------------------------------------------------------


def test_malformed_secure_boot_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(
        synthetic_corpus, "mokutil_test_ubuntu-24.04_malformed-secure-boot.txt", invalid=True
    )
    with pytest.raises(ValueError, match=r"malformed SecureBoot line \(line 1\)"):
        parse_secure_boot_status(text)


def test_malformed_setup_mode_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(
        synthetic_corpus, "mokutil_test_ubuntu-24.04_malformed-setup-mode.txt", invalid=True
    )
    with pytest.raises(ValueError, match=r"malformed SetupMode line \(line 2\)"):
        parse_secure_boot_status(text)


@pytest.mark.parametrize("name", sorted(_INVALID_FIXTURES))
def test_every_invalid_fixture_is_rejected(synthetic_corpus: Path, name: str) -> None:
    text = _load(synthetic_corpus, name, invalid=True)
    with pytest.raises(ValueError):
        parse_secure_boot_status(text)


# ---------------------------------------------------------------------------
# purity / independence
# ---------------------------------------------------------------------------


def test_parser_module_imports_nothing_but_stdlib_typing_and_its_own_models() -> None:
    """AST-based, not a substring search - this module's own docstring
    legitimately *discusses* subprocess/CommandRunner/Typer/Rich as
    things it does not depend on, so a naive text search over the whole
    file would false-positive on its own documentation.
    """
    import ast

    import bcs.platform.adapters.secureboot.parser as parser_module

    source = Path(parser_module.__file__).read_text(encoding="utf-8")
    imported_modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden = {
        "subprocess",
        "typer",
        "rich",
        "click",
        "bcs.platform.execution",
        "bcs.context",
        "bcs.app",
        "bcs.inventory",
        "bcs.platform.adapters.efi",
        "bcs.platform.adapters.storage",
    }
    assert not imported_modules & forbidden
    assert imported_modules == {
        "__future__",
        "re",
        "typing",
        "bcs.platform.adapters.secureboot.models",
    }
