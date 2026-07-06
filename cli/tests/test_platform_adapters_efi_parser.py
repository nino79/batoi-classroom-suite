"""Tests for the pure EFI parser.

Per the fixture corpus's own placeholder rules
(``tests/fixtures/README.md``), the real corpus
(``tests/fixtures/firmware/``) currently holds only zero-byte
placeholders - no real ``efibootmgr`` capture exists yet. These tests
therefore build a *temporary*, ``tmp_path``-rooted corpus (mirroring
``tests/fixtures/``'s own layout) and load every scenario through
``fixture_utils.py``, exactly as real captures will be loaded once they
exist - never by passing an inline string straight to the parser. The
real corpus is never written to.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from bcs.platform.adapters.efi.parser import parse_firmware_boot_configuration
from fixture_utils import load_fixture

_UBUNTU_DEVICE_PATH = (
    r"HD(1,GPT,aaaaaaaa-0000-0000-0000-000000000000,0x800,0x100000)/File(\EFI\ubuntu\shimx64.efi)"
)
_WINDOWS_DEVICE_PATH = (
    r"HD(1,GPT,bbbbbbbb-0000-0000-0000-000000000000,0x800,0x100000)"
    r"/File(\EFI\Microsoft\Boot\bootmgfw.efi)"
)
_RECOVERY_DEVICE_PATH = (
    r"HD(1,GPT,cccccccc-0000-0000-0000-000000000000,0x800,0x100000)/File(\EFI\ubuntu\recovery.efi)"
)

_VALID_FIXTURES: dict[str, str] = {
    "efibootmgr_test_ubuntu-24.04_single-boot.txt": (
        "BootCurrent: 0000\n"
        "Timeout: 1 seconds\n"
        "BootOrder: 0000\n"
        f"Boot0000* ubuntu\t{_UBUNTU_DEVICE_PATH}\n"
    ),
    "efibootmgr_test_ubuntu-24.04_dual-boot-windows.txt": (
        "BootCurrent: 0000\n"
        "Timeout: 1 seconds\n"
        "BootOrder: 0000,0001\n"
        f"Boot0000* ubuntu\t{_UBUNTU_DEVICE_PATH}\n"
        f"Boot0001* Windows Boot Manager\t{_WINDOWS_DEVICE_PATH}\n"
    ),
    "efibootmgr_test_ubuntu-24.04_boot-next-set.txt": (
        "BootCurrent: 0000\n"
        "Timeout: 1 seconds\n"
        "BootNext: 0001\n"
        "BootOrder: 0000,0001\n"
        f"Boot0000* ubuntu\t{_UBUNTU_DEVICE_PATH}\n"
        f"Boot0001  recovery\t{_RECOVERY_DEVICE_PATH}\n"
    ),
    "efibootmgr_test_ubuntu-24.04_unknown-lines.txt": (
        "BootCurrent: 0000\n"
        "SomeFutureField: something this parser does not know about\n"
        "Timeout: 1 seconds\n"
        "# not a real efibootmgr line\n"
        "BootOrder: 0000\n"
        f"Boot0000* ubuntu\t{_UBUNTU_DEVICE_PATH}\n"
    ),
    "efibootmgr_test_ubuntu-24.04_no-recognized-lines.txt": (
        "This file contains no efibootmgr-shaped lines at all.\nJust prose.\n"
    ),
    "efibootmgr_test_ubuntu-24.04_entry-no-device-path.txt": (
        "BootCurrent: 0000\nBoot0000* label-only\n"
    ),
    "efibootmgr_test_ubuntu-24.04_blank-lines-and-empty-values.txt": (
        "BootCurrent: 0000\n"
        "\n"
        "Timeout: 1 seconds\n"
        "BootNext: \n"
        "BootOrder: \n"
        f"Boot0000* ubuntu\t{_UBUNTU_DEVICE_PATH}\n"
    ),
}

_INVALID_FIXTURES: dict[str, str] = {
    "efibootmgr_test_ubuntu-24.04_malformed-boot-current.txt": (
        "BootCurrent: not-hex\nTimeout: 1 seconds\n"
    ),
    "efibootmgr_test_ubuntu-24.04_malformed-timeout.txt": (
        "BootCurrent: 0000\nTimeout: not-a-number seconds\n"
    ),
    "efibootmgr_test_ubuntu-24.04_malformed-boot-order.txt": ("BootOrder: 0000,bogus\n"),
    "efibootmgr_test_ubuntu-24.04_malformed-boot-next.txt": ("BootNext: zz\n"),
    "efibootmgr_test_ubuntu-24.04_duplicate-entries.txt": (
        f"Boot0000* ubuntu\t{_UBUNTU_DEVICE_PATH}\nBoot0000* duplicate\t{_WINDOWS_DEVICE_PATH}\n"
    ),
}


@pytest.fixture
def synthetic_corpus(tmp_path: Path) -> Path:
    """A temporary corpus, mirroring tests/fixtures/'s own layout, holding
    synthetic-but-realistic scenarios for parser correctness only. Never
    writes to the real corpus.
    """
    valid_dir = tmp_path / "firmware" / "generic"
    invalid_dir = tmp_path / "firmware" / "generic-invalid"
    valid_dir.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)
    for name, content in _VALID_FIXTURES.items():
        (valid_dir / name).write_text(content, encoding="utf-8")
    for name, content in _INVALID_FIXTURES.items():
        (invalid_dir / name).write_text(content, encoding="utf-8")
    return tmp_path


def _load(root: Path, name: str, *, invalid: bool = False) -> str:
    category = "generic-invalid" if invalid else "generic"
    return load_fixture("firmware", category, name, root=root)


# ---------------------------------------------------------------------------
# well-formed scenarios
# ---------------------------------------------------------------------------


def test_single_boot_entry(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "efibootmgr_test_ubuntu-24.04_single-boot.txt")
    config = parse_firmware_boot_configuration(text)

    assert config.current_boot_number == "0000"
    assert config.timeout_seconds == 1
    assert config.boot_order == ("0000",)
    assert config.boot_next is None
    assert len(config.entries) == 1
    entry = config.entries[0]
    assert entry.boot_number == "0000"
    assert entry.label == "ubuntu"
    assert entry.active is True
    assert entry.device_path == _UBUNTU_DEVICE_PATH
    assert entry.raw_line.startswith("Boot0000*")
    assert config.raw_text == text


def test_dual_boot_preserves_source_order(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "efibootmgr_test_ubuntu-24.04_dual-boot-windows.txt")
    config = parse_firmware_boot_configuration(text)

    assert config.boot_order == ("0000", "0001")
    assert [entry.boot_number for entry in config.entries] == ["0000", "0001"]
    assert config.entries[1].label == "Windows Boot Manager"


def test_boot_next_and_inactive_entry(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "efibootmgr_test_ubuntu-24.04_boot-next-set.txt")
    config = parse_firmware_boot_configuration(text)

    assert config.boot_next == "0001"
    recovery = config.entries[1]
    assert recovery.boot_number == "0001"
    assert recovery.label == "recovery"
    assert recovery.active is False


def test_unrecognized_lines_are_ignored_not_fatal(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "efibootmgr_test_ubuntu-24.04_unknown-lines.txt")
    config = parse_firmware_boot_configuration(text)

    assert config.current_boot_number == "0000"
    assert config.timeout_seconds == 1
    assert len(config.entries) == 1


def test_no_recognized_lines_yields_all_defaults(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "efibootmgr_test_ubuntu-24.04_no-recognized-lines.txt")
    config = parse_firmware_boot_configuration(text)

    assert config.current_boot_number is None
    assert config.timeout_seconds is None
    assert config.boot_order == ()
    assert config.boot_next is None
    assert config.entries == ()
    assert config.raw_text == text


def test_entry_with_no_device_path_segment(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "efibootmgr_test_ubuntu-24.04_entry-no-device-path.txt")
    config = parse_firmware_boot_configuration(text)

    assert config.entries[0].label == "label-only"
    assert config.entries[0].device_path == ""


def test_blank_lines_are_skipped_and_empty_values_mean_absent(synthetic_corpus: Path) -> None:
    """A blank line between recognized lines does not disrupt parsing, and
    an empty value after a recognized prefix (e.g. 'BootNext: ' with
    nothing following) means 'absent,' not malformed.
    """
    text = _load(synthetic_corpus, "efibootmgr_test_ubuntu-24.04_blank-lines-and-empty-values.txt")
    config = parse_firmware_boot_configuration(text)

    assert config.current_boot_number == "0000"
    assert config.timeout_seconds == 1
    assert config.boot_next is None
    assert config.boot_order == ()
    assert len(config.entries) == 1


@pytest.mark.parametrize("name", sorted(_VALID_FIXTURES))
def test_every_valid_fixture_parses_without_error(synthetic_corpus: Path, name: str) -> None:
    text = _load(synthetic_corpus, name)
    config = parse_firmware_boot_configuration(text)
    assert config.raw_text == text


# ---------------------------------------------------------------------------
# malformed mandatory fields - rejected, not silently ignored
# ---------------------------------------------------------------------------


def test_malformed_boot_current_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(
        synthetic_corpus, "efibootmgr_test_ubuntu-24.04_malformed-boot-current.txt", invalid=True
    )
    with pytest.raises(ValueError, match=r"malformed BootCurrent line \(line 1\)"):
        parse_firmware_boot_configuration(text)


def test_malformed_timeout_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(
        synthetic_corpus, "efibootmgr_test_ubuntu-24.04_malformed-timeout.txt", invalid=True
    )
    with pytest.raises(ValueError, match=r"malformed Timeout line \(line 2\)"):
        parse_firmware_boot_configuration(text)


def test_malformed_boot_order_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(
        synthetic_corpus, "efibootmgr_test_ubuntu-24.04_malformed-boot-order.txt", invalid=True
    )
    with pytest.raises(ValueError, match=r"malformed BootOrder line \(line 1\)"):
        parse_firmware_boot_configuration(text)


def test_malformed_boot_next_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(
        synthetic_corpus, "efibootmgr_test_ubuntu-24.04_malformed-boot-next.txt", invalid=True
    )
    with pytest.raises(ValueError, match=r"malformed BootNext line \(line 1\)"):
        parse_firmware_boot_configuration(text)


def test_duplicate_boot_numbers_raise_validation_error(synthetic_corpus: Path) -> None:
    text = _load(
        synthetic_corpus, "efibootmgr_test_ubuntu-24.04_duplicate-entries.txt", invalid=True
    )
    with pytest.raises(ValidationError, match="duplicate boot_number"):
        parse_firmware_boot_configuration(text)


@pytest.mark.parametrize("name", sorted(_INVALID_FIXTURES))
def test_every_invalid_fixture_is_rejected(synthetic_corpus: Path, name: str) -> None:
    text = _load(synthetic_corpus, name, invalid=True)
    with pytest.raises((ValueError, ValidationError)):
        parse_firmware_boot_configuration(text)


# ---------------------------------------------------------------------------
# purity / independence
# ---------------------------------------------------------------------------


def test_parser_module_imports_nothing_but_stdlib_typing_and_its_own_models() -> None:
    """AST-based, not a substring search - this module's own docstring
    legitimately *discusses* subprocess/CommandRunner/Typer/Rich as
    things it does not depend on, so a naive text search over the
    whole file would false-positive on its own documentation.
    """
    import ast

    import bcs.platform.adapters.efi.parser as parser_module

    source = Path(parser_module.__file__).read_text(encoding="utf-8")
    imported_modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden = {"subprocess", "typer", "rich", "bcs.platform.execution", "bcs.context", "bcs.app"}
    assert not imported_modules & forbidden
    assert imported_modules == {"__future__", "re", "typing", "bcs.platform.adapters.efi.models"}
