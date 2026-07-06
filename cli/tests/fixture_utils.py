"""Shared helpers for loading the captured-tool-output fixture corpus.

The corpus itself lives in ``tests/fixtures/`` - see its ``README.md``
for the collection, locale, anonymization, naming, and placeholder
rules these helpers enforce the mechanical half of. Every adapter's
tests (the EFI adapter today; ``storage``/``secureboot``/``filesystem``
adapters later) load fixtures through this module rather than with ad
hoc ``open()`` calls, so placeholder handling stays uniform: a
zero-byte ``.txt`` file is a *placeholder* (a needed-but-not-yet-
captured scenario), never valid parser input.

This is test infrastructure only - it is not part of the installed
``bcs`` package and contains no business logic.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

#: The corpus root. The single source of truth for where fixtures live.
FIXTURES_ROOT = Path(__file__).parent / "fixtures"


def fixture_path(*parts: str, root: Path = FIXTURES_ROOT) -> Path:
    """Resolve a fixture file's path, e.g. ``fixture_path("firmware",
    "generic", "efibootmgr_18_ubuntu-24.04_single-boot.txt")``.

    Raises ``FileNotFoundError`` (with the resolved path in the message)
    if the file does not exist - a typo'd fixture name should fail
    loudly at the call site, not surface later as an unrelated error.
    """
    path = root.joinpath(*parts)
    if not path.is_file():
        msg = f"fixture not found: {path} (see tests/fixtures/README.md)"
        raise FileNotFoundError(msg)
    return path


def is_placeholder(path: Path) -> bool:
    """Whether ``path`` is a zero-byte placeholder, per the corpus rules."""
    return path.stat().st_size == 0


def load_fixture(*parts: str, root: Path = FIXTURES_ROOT) -> str:
    """Read a fixture file's verbatim text (UTF-8).

    Refuses to load a placeholder: an empty string is never a real
    captured tool output, and silently feeding one to a parser test
    would make the test pass vacuously instead of failing visibly.
    """
    path = fixture_path(*parts, root=root)
    if is_placeholder(path):
        msg = (
            f"fixture {path} is an empty placeholder awaiting a real capture; "
            "see tests/fixtures/README.md for the collection rules"
        )
        raise ValueError(msg)
    return path.read_text(encoding="utf-8")


def iter_fixtures(
    *parts: str,
    root: Path = FIXTURES_ROOT,
    include_placeholders: bool = False,
) -> Iterator[Path]:
    """Yield every ``.txt`` fixture under a corpus directory, recursively.

    ``iter_fixtures("firmware")`` walks all vendor subdirectories in
    deterministic (sorted) order - the shape parametrized parser tests
    are expected to use, so a newly captured fixture is picked up by
    the suite without editing any test. Placeholders are skipped unless
    ``include_placeholders`` is true; ``README.md`` files are never
    yielded (they are not ``.txt``).

    Raises ``NotADirectoryError`` if the directory does not exist, so a
    typo'd category name fails loudly rather than yielding nothing.
    """
    directory = root.joinpath(*parts)
    if not directory.is_dir():
        msg = f"fixture directory not found: {directory} (see tests/fixtures/README.md)"
        raise NotADirectoryError(msg)
    for path in sorted(directory.rglob("*.txt")):
        if include_placeholders or not is_placeholder(path):
            yield path


__all__ = [
    "FIXTURES_ROOT",
    "fixture_path",
    "is_placeholder",
    "iter_fixtures",
    "load_fixture",
]
