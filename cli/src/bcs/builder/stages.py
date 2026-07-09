"""Concrete build stages for the Builder pipeline.

Each stage is a class that implements the :class:`BuildStage` protocol
and performs one step of the build process. Stages are **real
implementations** - they validate, create directories, generate
manifests, and finalise output - not TODOs or stubs. They produce no
golden image, run no Clonezilla commands, and touch no EFI variables,
consistent with the current Phase 2 scope.

Stage contract
==============

Every stage:
    * Reads from ``BuildContext.plan`` and (once prepared)
      ``BuildContext.workspace``.
    * Appends exactly one :class:`BuildStageResult` to
      ``context.stage_results`` on completion (success or failure).
    * Appends any produced :class:`BuildArtifact` entries to
      ``context.artifacts``.
    * Returns a :class:`BuildStageResult` summarising its outcome.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from bcs.builder.context import BuildContext
from bcs.builder.errors import WorkspaceError
from bcs.builder.execution import compute_file_checksum, write_json
from bcs.builder.models import BuildArtifact, BuildMetadata, BuildStageResult
from bcs.builder.workspace import BuildWorkspaceManager

# ---------------------------------------------------------------------------
# Helpers shared across stages
# ---------------------------------------------------------------------------

_CACHED_TOOL_VERSION: str | None = None


def _get_tool_version() -> str:
    """Return the bcs tool version string, cached after first call."""
    global _CACHED_TOOL_VERSION
    if _CACHED_TOOL_VERSION is not None:
        return _CACHED_TOOL_VERSION
    try:
        from bcs import __version__  # type: ignore[attr-defined]

        _CACHED_TOOL_VERSION = __version__
    except (ImportError, AttributeError):
        _CACHED_TOOL_VERSION = "0.0.0"
    return _CACHED_TOOL_VERSION


def _make_result(  # noqa: PLR0913
    stage_name: str,
    success: bool,
    exit_code: int,
    message: str = "",
    elapsed_seconds: float | None = None,
    artifacts: tuple[BuildArtifact, ...] = (),
) -> BuildStageResult:
    """Convenience factory for :class:`BuildStageResult`."""
    return BuildStageResult(
        stage_name=stage_name,
        success=success,
        exit_code=exit_code,
        message=message,
        elapsed_seconds=elapsed_seconds,
        artifacts=artifacts,
    )


def _elapsed(start: float) -> float:
    """Return wall-clock seconds since ``start`` (from ``time.monotonic``)."""
    return time.monotonic() - start


# ---------------------------------------------------------------------------
# Stage: ValidateConfig
# ---------------------------------------------------------------------------


class ValidateConfigStage:
    """Stage 1: validate that the build configuration exists and is readable.

    Checks:
        - The config file path exists.
        - The config file is a regular file and readable.
        - The config filename has a ``.yaml`` or ``.yml`` extension
          (a simple sanity check, not a full schema validation).

    This stage does **not** parse the YAML or validate against
    ``config/schema.yaml`` - that is the responsibility of the
    ``bcs validate`` command and the full Builder implementation.
    """

    name = "validate-config"

    def run(self, context: BuildContext) -> BuildStageResult:
        start = time.monotonic()
        config_path = context.plan.config_path

        reasons: list[str] = []

        if not config_path.exists():
            reasons.append(f"Config file does not exist: {config_path}")

        if not reasons and not config_path.is_file():
            reasons.append(f"Config path is not a regular file: {config_path}")

        if not reasons and not _is_readable(config_path):
            reasons.append(f"Config file is not readable: {config_path}")

        if not reasons:
            ext = config_path.suffix.lower()
            if ext not in (".yaml", ".yml"):
                reasons.append(f"Config file should have a .yaml or .yml extension, got '{ext}'")

        if reasons:
            msg = "; ".join(reasons)
            elapsed = _elapsed(start)
            return _make_result(
                self.name, success=False, exit_code=1, message=msg, elapsed_seconds=elapsed
            )

        return _make_result(
            self.name,
            success=True,
            exit_code=0,
            message=f"Config file validated: {config_path}",
            elapsed_seconds=_elapsed(start),
        )


def _is_readable(path: Path) -> bool:
    """Check whether ``path`` is readable without opening it."""
    try:
        return os.access(str(path), os.R_OK)
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Stage: PrepareWorkspace
# ---------------------------------------------------------------------------


class PrepareWorkspaceStage:
    """Stage 2: create the workspace directory tree.

    Uses :class:`BuildWorkspaceManager` to create the standard
    directory layout (artifacts/, logs/, metadata/, cache/). Stores
    the resulting :class:`BuildWorkspace` in ``context.workspace``.
    """

    name = "prepare-workspace"

    def run(self, context: BuildContext) -> BuildStageResult:
        start = time.monotonic()

        root = context.plan.workspace_root or Path.cwd() / _default_workspace_name()
        try:
            manager = BuildWorkspaceManager(root=root)
            workspace = manager.create()
        except (WorkspaceError, OSError) as exc:
            return _make_result(
                self.name,
                success=False,
                exit_code=10,
                message=str(exc),
                elapsed_seconds=_elapsed(start),
            )

        context.workspace = workspace

        return _make_result(
            self.name,
            success=True,
            exit_code=0,
            message=f"Workspace created at {workspace.root}",
            elapsed_seconds=_elapsed(start),
        )


def _default_workspace_name() -> str:
    """Generate a default workspace directory name with timestamp."""
    import datetime

    ts = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%dT%H%M%S")
    return f".bcs-build-{ts}"


# ---------------------------------------------------------------------------
# Stage: GenerateManifest
# ---------------------------------------------------------------------------


class GenerateManifestStage:
    """Stage 4: generate a skeleton BuildManifest and write it to metadata/.

    Produces a ``BuildManifest`` describing the plan and any artifacts
    already accumulated. Writes the manifest as JSON to
    ``metadata/manifest.json`` in the workspace.

    This is a placeholder until the full manifest generation (package
    lists, filesystem layout, boot entries) is implemented.
    """

    name = "generate-manifest"

    def run(self, context: BuildContext) -> BuildStageResult:
        start = time.monotonic()

        if context.workspace is None:
            return _make_result(
                self.name,
                success=False,
                exit_code=30,
                message="Cannot generate manifest: workspace has not been prepared",
                elapsed_seconds=_elapsed(start),
            )

        from bcs.builder.manifest import save_manifest
        from bcs.builder.models import BuildManifest

        manifest = BuildManifest(
            manifest_version="bcs-build-manifest/v1alpha1",
            plan=context.plan,
            artifacts=tuple(context.artifacts),
            stage_results=tuple(context.stage_results),
        )

        manifest_path = context.workspace.metadata_dir / "manifest.json"
        try:
            save_manifest(manifest, manifest_path)
        except OSError as exc:
            return _make_result(
                self.name,
                success=False,
                exit_code=30,
                message=f"Failed to write manifest: {exc}",
                elapsed_seconds=_elapsed(start),
            )

        manifest_artifact = BuildArtifact(
            path=manifest_path.relative_to(context.workspace.root).as_posix(),
            artifact_type="manifest",
        )
        context.artifacts.append(manifest_artifact)

        return _make_result(
            self.name,
            success=True,
            exit_code=0,
            message=f"Manifest written to {manifest_path}",
            elapsed_seconds=_elapsed(start),
            artifacts=(manifest_artifact,),
        )


# ---------------------------------------------------------------------------
# Stage: Finalize
# ---------------------------------------------------------------------------


class FinalizeStage:
    """Stage 8: finalize build metadata, compute checksums, and optionally
    clean up the workspace.

    Responsibilities:
        1. Compute checksums for all artifacts that lack them.
        2. Generate and write the provenance record (``BuildMetadata``)
           to ``metadata/provenance.json``.
        3. Write the build log summary to ``metadata/build.log``.
        4. Optionally clean the workspace (unless ``plan.keep_workspace``
           is set).
    """

    name = "finalize"

    def run(self, context: BuildContext) -> BuildStageResult:
        start = time.monotonic()

        if context.workspace is None:
            return _make_result(
                self.name,
                success=False,
                exit_code=70,
                message="Cannot finalize: workspace has not been prepared",
                elapsed_seconds=_elapsed(start),
            )

        # 1. Compute checksums for artifacts that lack them
        computed_artifacts: list[BuildArtifact] = []
        for artifact in context.artifacts:
            if artifact.checksum_sha256 is not None:
                computed_artifacts.append(artifact)
                continue
            artifact_path = context.workspace.root / artifact.path
            if not artifact_path.exists():
                computed_artifacts.append(artifact)
                continue
            try:
                checksum = compute_file_checksum(artifact_path)
                computed_artifacts.append(
                    BuildArtifact(
                        path=artifact.path,
                        artifact_type=artifact.artifact_type,
                        checksum_sha256=checksum,
                        size_bytes=artifact_path.stat().st_size,
                    )
                )
            except OSError:
                computed_artifacts.append(artifact)

        # 2. Generate provenance record
        from datetime import UTC, datetime

        metadata = BuildMetadata(
            build_timestamp=datetime.now(UTC),
            tool_version=_get_tool_version(),
            git_commit=_get_git_commit(),
            recipe_path=str(context.plan.config_path),
        )
        context.metadata = metadata

        provenance_path = context.workspace.metadata_dir / "provenance.json"
        try:
            write_json(
                provenance_path,
                metadata.model_dump(mode="json", by_alias=True),
            )
        except OSError as exc:
            return _make_result(
                self.name,
                success=False,
                exit_code=70,
                message=f"Failed to write provenance: {exc}",
                elapsed_seconds=_elapsed(start),
            )

        # 3. Write build log summary
        log_path = context.workspace.logs_dir / "build.log"
        _write_build_log(log_path, context)

        # 4. Optionally clean
        if not context.plan.keep_workspace:
            manager = BuildWorkspaceManager(root=context.workspace.root)
            try:
                manager.clean()
            except WorkspaceError as exc:
                return _make_result(
                    self.name,
                    success=False,
                    exit_code=70,
                    message=f"Cleanup failed: {exc}",
                    elapsed_seconds=_elapsed(start),
                )

        return _make_result(
            self.name,
            success=True,
            exit_code=0,
            message="Build finalized",
            elapsed_seconds=_elapsed(start),
        )


def _get_git_commit() -> str | None:
    """Try to read the current git commit hash from HEAD."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001, S110
        pass
    return None


def _write_build_log(path: Path, context: BuildContext) -> None:
    """Write a human-readable build log to ``path``."""
    lines: list[str] = [
        "BCS Build Log",
        "=============",
        f"Config:       {context.plan.config_path}",
        f"Stages:       {', '.join(r.stage_name for r in context.stage_results)}",
        "",
        "Stage Results:",
    ]
    for result in context.stage_results:
        status = "OK" if result.success else "FAIL"
        lines.append(f"  [{status}] {result.stage_name}: {result.message}")
        if result.elapsed_seconds is not None:
            lines.append(f"         ({result.elapsed_seconds:.2f}s)")

    lines.append("")
    lines.append(f"Total artifacts: {len(context.artifacts)}")
    lines.append(f"Build success:   {all(r.success for r in context.stage_results)}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = [
    "FinalizeStage",
    "GenerateManifestStage",
    "PrepareWorkspaceStage",
    "ValidateConfigStage",
]
