"""Tests for the fixture-loading helpers, plus corpus hygiene guards.

The tmp_path-based tests exercise the helpers against loader-specific
test data (arbitrary text), NOT against the real corpus - fabricated
tool output never goes into tests/fixtures/ itself, per its README.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fixture_utils import (
    FIXTURES_ROOT,
    fixture_path,
    is_placeholder,
    iter_fixtures,
    load_fixture,
)

_A_PLACEHOLDER = ("firmware", "generic", "efibootmgr_unknown_ubuntu-24.04_single-boot.txt")


@pytest.fixture
def fake_corpus(tmp_path: Path) -> Path:
    """A miniature corpus layout for exercising the helpers in isolation."""
    (tmp_path / "firmware" / "generic").mkdir(parents=True)
    (tmp_path / "firmware" / "dell").mkdir()
    (tmp_path / "firmware" / "README.md").write_text("docs, not a fixture\n", encoding="utf-8")
    (tmp_path / "firmware" / "generic" / "tool_1_os_real.txt").write_text(
        "loader test data line\n", encoding="utf-8"
    )
    (tmp_path / "firmware" / "generic" / "tool_unknown_os_empty.txt").touch()
    (tmp_path / "firmware" / "dell" / "tool_1_os_nested.txt").write_text(
        "nested loader test data\n", encoding="utf-8"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# fixture_path
# ---------------------------------------------------------------------------


def test_fixtures_root_exists() -> None:
    assert FIXTURES_ROOT.is_dir()


def test_fixture_path_resolves_an_existing_repo_placeholder() -> None:
    path = fixture_path(*_A_PLACEHOLDER)
    assert path.is_file()
    assert path.name == _A_PLACEHOLDER[-1]


def test_fixture_path_missing_file_raises_with_path_and_hint() -> None:
    with pytest.raises(FileNotFoundError, match=r"no-such-fixture\.txt.*README"):
        fixture_path("firmware", "no-such-fixture.txt")


# ---------------------------------------------------------------------------
# is_placeholder / load_fixture
# ---------------------------------------------------------------------------


def test_repo_placeholder_is_detected_as_placeholder() -> None:
    assert is_placeholder(fixture_path(*_A_PLACEHOLDER)) is True


def test_load_fixture_refuses_a_placeholder() -> None:
    with pytest.raises(ValueError, match="empty placeholder awaiting a real capture"):
        load_fixture(*_A_PLACEHOLDER)


def test_load_fixture_reads_real_content(fake_corpus: Path) -> None:
    text = load_fixture("firmware", "generic", "tool_1_os_real.txt", root=fake_corpus)
    assert text == "loader test data line\n"


def test_load_fixture_missing_file_raises(fake_corpus: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_fixture("firmware", "generic", "absent.txt", root=fake_corpus)


# ---------------------------------------------------------------------------
# iter_fixtures
# ---------------------------------------------------------------------------


def test_iter_fixtures_skips_placeholders_and_readmes(fake_corpus: Path) -> None:
    names = [path.name for path in iter_fixtures("firmware", root=fake_corpus)]
    assert names == ["tool_1_os_nested.txt", "tool_1_os_real.txt"]


def test_iter_fixtures_recurses_into_subdirectories(fake_corpus: Path) -> None:
    parents = {path.parent.name for path in iter_fixtures("firmware", root=fake_corpus)}
    assert parents == {"generic", "dell"}


def test_iter_fixtures_can_include_placeholders(fake_corpus: Path) -> None:
    names = [
        path.name for path in iter_fixtures("firmware", root=fake_corpus, include_placeholders=True)
    ]
    assert "tool_unknown_os_empty.txt" in names
    assert len(names) == 3


def test_iter_fixtures_missing_directory_raises(fake_corpus: Path) -> None:
    with pytest.raises(NotADirectoryError, match="no-such-category"):
        list(iter_fixtures("no-such-category", root=fake_corpus))


def test_iter_fixtures_on_real_corpus_yields_nothing_yet() -> None:
    """Every current repo fixture is a placeholder - the corpus holds no
    captured output yet. This test documents that state; it is expected
    to be updated (not deleted) when the first real capture lands.
    """
    assert list(iter_fixtures()) == []


# ---------------------------------------------------------------------------
# corpus hygiene guards - conventions from tests/fixtures/README.md,
# enforced mechanically over whatever the corpus currently contains
# ---------------------------------------------------------------------------

_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9.-]*(?:_[a-z0-9][a-z0-9.-]*){3}\.txt")

_ALL_CORPUS_FILES = sorted(FIXTURES_ROOT.rglob("*.txt"))


def test_corpus_contains_the_tracked_placeholder_scenarios() -> None:
    assert len(_ALL_CORPUS_FILES) >= 6  # the initial placeholder set


@pytest.mark.parametrize("path", _ALL_CORPUS_FILES, ids=lambda p: p.name)
def test_corpus_file_names_follow_the_naming_convention(path: Path) -> None:
    assert _NAME_PATTERN.fullmatch(path.name), (
        f"{path} violates the <tool>_<version>_<platform>_<scenario>.txt "
        "convention in tests/fixtures/README.md"
    )


@pytest.mark.parametrize("path", _ALL_CORPUS_FILES, ids=lambda p: p.name)
def test_corpus_file_is_utf8_and_unknown_version_only_on_placeholders(path: Path) -> None:
    path.read_text(encoding="utf-8")  # must not raise
    if "_unknown_" in path.name:
        assert is_placeholder(path), (
            f"{path} has real content but an 'unknown' name field - capture "
            "provenance and rename it, per tests/fixtures/README.md"
        )
