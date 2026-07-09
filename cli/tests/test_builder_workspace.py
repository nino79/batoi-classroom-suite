from __future__ import annotations

from pathlib import Path

import pytest

from bcs.builder.errors import WorkspaceError
from bcs.builder.workspace import BuildWorkspaceManager


def test_create_workspace(tmp_path: Path) -> None:
    root = tmp_path / "mybuild"
    mgr = BuildWorkspaceManager(root=root)
    ws = mgr.create()
    assert ws.root == root
    assert ws.artifacts_dir == root / "artifacts"
    assert ws.logs_dir == root / "logs"
    assert ws.metadata_dir == root / "metadata"
    assert ws.cache_dir == root / "cache"
    assert ws.artifacts_dir.is_dir()
    assert ws.logs_dir.is_dir()
    assert ws.metadata_dir.is_dir()
    assert ws.cache_dir.is_dir()


def test_create_workspace_existing_empty(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    mgr = BuildWorkspaceManager(root=root)
    ws = mgr.create()
    assert ws.root == root


def test_create_workspace_existing_non_empty(tmp_path: Path) -> None:
    root = tmp_path / "nonempty"
    root.mkdir()
    (root / "existing.txt").write_text("hello")
    mgr = BuildWorkspaceManager(root=root)
    with pytest.raises(WorkspaceError, match="already exists and is not empty"):
        mgr.create()


def test_clean_workspace(tmp_path: Path) -> None:
    root = tmp_path / "toclean"
    mgr = BuildWorkspaceManager(root=root)
    mgr.create()
    assert root.is_dir()
    mgr.clean()
    assert not root.exists()


def test_clean_workspace_non_existent(tmp_path: Path) -> None:
    root = tmp_path / "neverexisted"
    mgr = BuildWorkspaceManager(root=root)
    mgr.clean()  # should not raise


def test_clean_workspace_removes_all_content(tmp_path: Path) -> None:
    root = tmp_path / "full"
    mgr = BuildWorkspaceManager(root=root)
    mgr.create()
    (root / "artifacts" / "output.txt").write_text("data")
    (root / "metadata" / "provenance.json").write_text("{}")
    mgr.clean()
    assert not root.exists()


def test_contains(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    mgr = BuildWorkspaceManager(root=root)
    mgr.create()
    assert mgr.contains(root / "artifacts" / "output.txt")
    assert mgr.contains(root / "metadata")
    assert not mgr.contains(tmp_path / "outside")


def test_contains_outside(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    mgr = BuildWorkspaceManager(root=root)
    mgr.create()
    # A path completely outside the workspace should not be contained
    assert not mgr.contains(tmp_path / "outside")


def test_root_property(tmp_path: Path) -> None:
    root = tmp_path / "mybuild"
    mgr = BuildWorkspaceManager(root=root)
    assert mgr.root == root.resolve()


def test_create_twice_fails(tmp_path: Path) -> None:
    root = tmp_path / "twice"
    mgr = BuildWorkspaceManager(root=root)
    mgr.create()
    with pytest.raises(WorkspaceError):
        mgr.create()


def test_workspace_has_expected_directory_structure(tmp_path: Path) -> None:
    root = tmp_path / "structured"
    mgr = BuildWorkspaceManager(root=root)
    ws = mgr.create()
    assert list(root.iterdir()) == [
        ws.artifacts_dir,
        ws.cache_dir,
        ws.logs_dir,
        ws.metadata_dir,
    ]
