from __future__ import annotations

import json
from pathlib import Path

import pytest

from bcs.builder.execution import (
    compute_file_checksum,
    copy_file,
    ensure_directory,
    read_json,
    write_json,
)

# ---------------------------------------------------------------------------
# ensure_directory
# ---------------------------------------------------------------------------


def test_ensure_directory_creates(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c"
    result = ensure_directory(target)
    assert result == target
    assert target.is_dir()


def test_ensure_directory_existing(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    result = ensure_directory(target)
    assert result == target
    assert target.is_dir()


def test_ensure_directory_nested(tmp_path: Path) -> None:
    target = tmp_path / "level1" / "level2" / "level3"
    result = ensure_directory(target)
    assert result == target
    assert target.is_dir()
    assert (tmp_path / "level1").is_dir()
    assert (tmp_path / "level1" / "level2").is_dir()


# ---------------------------------------------------------------------------
# compute_file_checksum
# ---------------------------------------------------------------------------


def test_compute_file_checksum_regular(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    cksum = compute_file_checksum(f)
    assert isinstance(cksum, str)
    assert len(cksum) == 64
    # known sha256 of "hello world\n" - wait, no newline needed
    # sha256 of "hello world" (no newline)
    assert cksum == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_compute_file_checksum_empty(tmp_path: Path) -> None:
    f = tmp_path / "empty.txt"
    f.write_text("")
    cksum = compute_file_checksum(f)
    assert cksum == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_compute_file_checksum_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compute_file_checksum(tmp_path / "nonexistent")


# ---------------------------------------------------------------------------
# copy_file
# ---------------------------------------------------------------------------


def test_copy_file_basic(tmp_path: Path) -> None:
    src = tmp_path / "source.txt"
    src.write_text("content")
    dst = tmp_path / "sub" / "dest.txt"
    result = copy_file(src, dst)
    assert result == dst
    assert dst.is_file()
    assert dst.read_text() == "content"


def test_copy_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        copy_file(tmp_path / "nonexistent", tmp_path / "dest.txt")


# ---------------------------------------------------------------------------
# read_json / write_json
# ---------------------------------------------------------------------------


def test_write_json_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "data.json"
    write_json(target, {"key": "value", "num": 42})
    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data == {"key": "value", "num": 42}


def test_read_json_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    original = {"hello": "world", "list": [1, 2, 3]}
    write_json(target, original)
    loaded = read_json(target)
    assert loaded == original


def test_read_json_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_json(tmp_path / "nonexistent.json")


def test_read_json_invalid(tmp_path: Path) -> None:
    f = tmp_path / "bad.json"
    f.write_text("{invalid")
    with pytest.raises(json.JSONDecodeError):
        read_json(f)


def test_write_json_sort_keys(tmp_path: Path) -> None:
    target = tmp_path / "sorted.json"
    write_json(target, {"z": 1, "a": 2})
    content = target.read_text(encoding="utf-8")
    # sort_keys=True should put "a" before "z"
    assert content.index("a") < content.index("z")
