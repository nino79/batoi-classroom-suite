"""Tests for the pure Filesystem parser.

Per the fixture corpus's own placeholder rules
(``tests/fixtures/README.md``), the real corpus
(``tests/fixtures/filesystem/``) currently holds no scenario files at
all - the design's fixtures-strategy follow-up (populating that
directory) has not happened yet. These tests therefore build a
*temporary*, ``tmp_path``-rooted corpus (mirroring ``tests/fixtures/``'s
own layout) and load every scenario through ``fixture_utils.py``,
exactly as real captures will be loaded once they exist - never by
passing an inline string straight to the parser. The real corpus is
never written to.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bcs.platform.adapters.filesystem.parser import parse_filesystem_usage
from fixture_utils import load_fixture

# A realistic GNU df header for
# `df --output=source,fstype,itotal,iused,iavail,size,used,avail,target`.
# Its last column label is the real multi-word "Mounted on" - the split
# strategy must absorb it without needing this text hard-coded anywhere
# in the parser itself.
_HEADER_LINE = (
    "Filesystem     Type     Inodes  IUsed   IFree 1B-blocks       Used  Available Mounted on"
)

_VALID_FIXTURES: dict[str, str] = {
    "df_test_ubuntu-24.04_typical.txt": (
        f"{_HEADER_LINE}\n"
        "/dev/nvme0n1p2 ext4 32768000 512000 32256000 "
        "512110190592 128027547648 358486736896 /\n"
    ),
    "df_test_ubuntu-24.04_no-inode-support.txt": (
        "tmpfs tmpfs - - - 1073741824 1245184 1072496640 /run\n"
    ),
    "df_test_ubuntu-24.04_target-with-space.txt": (
        "/dev/sdb1 vfat - - - 1073741824 104857600 969019904 /media/USB DRIVE\n"
    ),
    "df_test_ubuntu-24.04_duplicate-target.txt": (
        "/dev/nvme0n1p3 ext4 1000 100 900 1073741824 104857600 969019904 /mnt/shared\n"
        "tmpfs tmpfs - - - 1073741824 0 1073741824 /mnt/shared\n"
    ),
    "df_test_ubuntu-24.04_blank-lines.txt": (
        "\n"
        f"{_HEADER_LINE}\n"
        "\n"
        "/dev/nvme0n1p2 ext4 32768000 512000 32256000 "
        "512110190592 128027547648 358486736896 /\n"
        "\n"
    ),
    "df_test_ubuntu-24.04_header-only.txt": f"{_HEADER_LINE}\n",
}

_INVALID_FIXTURES: dict[str, str] = {
    "df_test_ubuntu-24.04_short-row.txt": "/dev/nvme0n1p2 ext4 32768000\n",
    "df_test_ubuntu-24.04_malformed-size.txt": (
        "/dev/nvme0n1p2 ext4 32768000 512000 32256000 abc 128027547648 358486736896 /\n"
    ),
}


@pytest.fixture
def synthetic_corpus(tmp_path: Path) -> Path:
    """A temporary corpus, mirroring tests/fixtures/'s own layout, holding
    synthetic-but-realistic scenarios for parser correctness only. Never
    writes to the real corpus.
    """
    valid_dir = tmp_path / "filesystem" / "generic"
    invalid_dir = tmp_path / "filesystem" / "generic-invalid"
    valid_dir.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)
    for name, content in _VALID_FIXTURES.items():
        (valid_dir / name).write_text(content, encoding="utf-8")
    for name, content in _INVALID_FIXTURES.items():
        (invalid_dir / name).write_text(content, encoding="utf-8")
    return tmp_path


def _load(root: Path, name: str, *, invalid: bool = False) -> str:
    category = "generic-invalid" if invalid else "generic"
    return load_fixture("filesystem", category, name, root=root)


# ---------------------------------------------------------------------------
# well-formed scenarios
# ---------------------------------------------------------------------------


def test_typical_row_parses(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_typical.txt")
    report = parse_filesystem_usage(text)

    assert len(report.filesystems) == 1
    entry = report.filesystems[0]
    assert entry.source == "/dev/nvme0n1p2"
    assert entry.target == "/"
    assert entry.fs_type == "ext4"
    assert entry.size_bytes == 512110190592
    assert entry.used_bytes == 128027547648
    assert entry.available_bytes == 358486736896
    assert entry.inodes_total == 32768000
    assert entry.inodes_used == 512000
    assert entry.inodes_available == 32256000
    assert report.raw_text == text
    assert report.raw_stderr == ""


def test_header_line_is_silently_skipped(synthetic_corpus: Path) -> None:
    """The header row has 9 whitespace-separated positions (its own
    'Mounted on' label absorbed into the target position by the split
    strategy), but none of its six numeric-position fields parse as a
    number or '-' - so it is skipped, not treated as a malformed row.
    """
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_header-only.txt")
    report = parse_filesystem_usage(text)

    assert report.filesystems == ()
    assert report.raw_text == text


def test_inode_dash_fields_parse_as_none(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_no-inode-support.txt")
    report = parse_filesystem_usage(text)

    assert len(report.filesystems) == 1
    entry = report.filesystems[0]
    assert entry.inodes_total is None
    assert entry.inodes_used is None
    assert entry.inodes_available is None
    assert entry.fs_type == "tmpfs"


def test_target_with_internal_whitespace_is_preserved_verbatim(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_target-with-space.txt")
    report = parse_filesystem_usage(text)

    assert len(report.filesystems) == 1
    assert report.filesystems[0].target == "/media/USB DRIVE"


def test_duplicate_target_rows_both_survive(synthetic_corpus: Path) -> None:
    """Mount stacking (overmounting) is a real condition - the parser
    never deduplicates or rejects it, per
    docs/FILESYSTEM_ADAPTER.md#domain-models.
    """
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_duplicate-target.txt")
    report = parse_filesystem_usage(text)

    assert len(report.filesystems) == 2
    assert report.filesystems[0].target == report.filesystems[1].target == "/mnt/shared"
    assert report.filesystems[0].source != report.filesystems[1].source


def test_blank_lines_are_tolerated(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_blank-lines.txt")
    report = parse_filesystem_usage(text)

    assert len(report.filesystems) == 1
    assert report.filesystems[0].target == "/"


def test_text_with_zero_data_rows_returns_empty_report_not_an_error(
    synthetic_corpus: Path,
) -> None:
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_header-only.txt")
    report = parse_filesystem_usage(text)

    assert report.filesystems == ()


def test_empty_input_returns_empty_report() -> None:
    """A genuinely empty string is a degenerate case the fixture corpus's
    own placeholder convention can't represent, so this is tested inline
    rather than through the synthetic corpus.
    """
    report = parse_filesystem_usage("")

    assert report.filesystems == ()
    assert report.raw_text == ""
    assert report.raw_stderr == ""


@pytest.mark.parametrize("name", sorted(_VALID_FIXTURES))
def test_every_valid_fixture_parses_without_error(synthetic_corpus: Path, name: str) -> None:
    text = _load(synthetic_corpus, name)
    report = parse_filesystem_usage(text)
    assert report.raw_text == text


def test_raw_stderr_is_always_empty_from_the_parser(synthetic_corpus: Path) -> None:
    """parse_filesystem_usage never sees stderr at all - attaching the
    real value is adapter.py's job, per docs/FILESYSTEM_ADAPTER.md#domain-models.
    """
    for name in _VALID_FIXTURES:
        text = _load(synthetic_corpus, name)
        assert parse_filesystem_usage(text).raw_stderr == ""


# ---------------------------------------------------------------------------
# malformed input - rejected, not silently ignored
# ---------------------------------------------------------------------------


def test_short_row_is_rejected_as_malformed_row(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_short-row.txt", invalid=True)
    with pytest.raises(ValueError, match=r"malformed row \(line 1\)"):
        parse_filesystem_usage(text)


def test_malformed_numeric_field_is_rejected_naming_the_field(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "df_test_ubuntu-24.04_malformed-size.txt", invalid=True)
    with pytest.raises(ValueError, match=r"malformed size line \(line 1\)"):
        parse_filesystem_usage(text)


@pytest.mark.parametrize("name", sorted(_INVALID_FIXTURES))
def test_every_invalid_fixture_is_rejected(synthetic_corpus: Path, name: str) -> None:
    text = _load(synthetic_corpus, name, invalid=True)
    with pytest.raises(ValueError):
        parse_filesystem_usage(text)


def test_malformed_field_names_the_first_failing_field_in_column_order() -> None:
    """Every numeric-position field but 'used' parses; the raised error
    must name exactly the one that failed, not a different one.
    """
    line = "/dev/nvme0n1p2 ext4 32768000 512000 32256000 512110190592 NOTANUMBER 358486736896 /"
    with pytest.raises(ValueError, match=r"malformed used line \(line 1\)"):
        parse_filesystem_usage(line)


def test_malformed_row_message_quotes_the_offending_line_verbatim() -> None:
    line = "only three tokens here"
    with pytest.raises(ValueError) as exc_info:
        parse_filesystem_usage(line)
    assert repr(line) in str(exc_info.value)


def test_malformed_row_with_remainder_but_no_target() -> None:
    """9 leading tokens exist but the final 'avail target' remainder has
    no whitespace to split target off of - also a malformed row, not a
    malformed field.
    """
    line = "src fstype 1 2 3 4 5 6"
    with pytest.raises(ValueError, match=r"malformed row \(line 1\)"):
        parse_filesystem_usage(line)


# ---------------------------------------------------------------------------
# purity / independence
# ---------------------------------------------------------------------------


def test_parser_module_imports_nothing_but_stdlib_and_its_own_models() -> None:
    """AST-based, not a substring search - this module's own docstring
    legitimately *discusses* subprocess/CommandRunner/Typer/Rich as
    things it does not depend on, so a naive text search over the whole
    file would false-positive on its own documentation.
    """
    import bcs.platform.adapters.filesystem.parser as parser_module

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
        "bcs.platform.adapters.secureboot",
    }
    assert not imported_modules & forbidden
    assert imported_modules == {
        "__future__",
        "re",
        "typing",
        "bcs.platform.adapters.filesystem.models",
    }
