"""Workspace management for the Builder pipeline.

The workspace is a temporary directory tree where all build stages
place their output. It follows a fixed layout:

.. code-block:: text

    <root>/
      artifacts/    # Final build output (images, provenance bundles)
      logs/         # Build logs and timing data
      metadata/     # Provenance, VERSION, manifest JSON files
      cache/        # Transient cached data (package lists, references)
"""

from __future__ import annotations

from pathlib import Path

from bcs.builder.errors import WorkspaceError
from bcs.builder.execution import ensure_directory
from bcs.builder.models import BuildWorkspace


class BuildWorkspaceManager:
    """Creates and manages a build workspace directory tree.

    Usage::

        mgr = BuildWorkspaceManager(root=Path("/tmp/my-build"))
        ws = mgr.create()

    The workspace is **not** created at construction time - call
    :meth:`create` explicitly when the pipeline is ready to start.
    """

    def __init__(self, root: Path) -> None:
        """Store the workspace root; does not touch the filesystem.

        Args:
            root: Absolute path to the workspace root. If the path
                already exists and is non-empty, :meth:`create` will
                raise :class:`WorkspaceError`.
        """
        self._root = root.resolve()

    @property
    def root(self) -> Path:
        """The resolved workspace root path."""
        return self._root

    def create(self) -> BuildWorkspace:
        """Create the workspace directory tree on disk.

        Returns a :class:`BuildWorkspace` model with all resolved,
        absolute paths. Raises :class:`WorkspaceError` if the root
        already exists as a non-empty directory.
        """
        if self._root.exists() and any(self._root.iterdir()):
            raise WorkspaceError(
                f"Workspace root already exists and is not empty: {self._root}",
                details={"path": str(self._root)},
            )

        try:
            artifacts_dir = ensure_directory(self._root / "artifacts")
            logs_dir = ensure_directory(self._root / "logs")
            metadata_dir = ensure_directory(self._root / "metadata")
            cache_dir = ensure_directory(self._root / "cache")
        except OSError as exc:
            raise WorkspaceError(
                f"Failed to create workspace directory: {exc}",
                details={"path": str(self._root), "error": str(exc)},
            ) from exc

        return BuildWorkspace(
            root=self._root,
            artifacts_dir=artifacts_dir,
            logs_dir=logs_dir,
            metadata_dir=metadata_dir,
            cache_dir=cache_dir,
        )

    def clean(self) -> None:
        """Remove the entire workspace directory tree.

        Safe to call even if the workspace does not exist (no-op in
        that case). Raises :class:`WorkspaceError` if removal fails
        for a reason other than non-existence.
        """
        if not self._root.exists():
            return
        try:
            import shutil

            shutil.rmtree(self._root)
        except OSError as exc:
            raise WorkspaceError(
                f"Failed to clean workspace: {exc}",
                details={"path": str(self._root), "error": str(exc)},
            ) from exc

    def contains(self, path: Path) -> bool:
        """Check whether ``path`` is inside the workspace root.

        Useful for stages that want to verify they are writing to a
        safe location.
        """
        try:
            resolved = path.resolve()
            return self._root in resolved.parents or resolved == self._root
        except OSError:
            return False


__all__ = ["BuildWorkspaceManager"]
