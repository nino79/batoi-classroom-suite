"""Immutable data models for the Builder subsystem.

Every model is **frozen** with ``extra="forbid"`` and
``populate_by_name=True``, matching the convention established by
``bcs.platform.models`` and ``bcs.inventory.models``. Fields use
``camelCase`` JSON aliases where the attribute name would differ from
the JSON serialization.

Models in this module carry **only data** - no business logic, no
filesystem interaction, no command execution.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class BuildPlan(BaseModel):
    """A resolved plan that drives one Builder invocation.

    Produced from a ``ClassroomConfig`` YAML (or from CLI overrides)
    before any stage executes. Describes *what* to build and *how*:
    which config to use, which stages to run, and whether to keep the
    workspace after completion.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    config_path: Path = Field(
        description="Absolute path to the ClassroomConfig YAML file.",
    )
    workspace_root: Path | None = Field(
        default=None,
        alias="workspaceRoot",
        description=(
            "Override path for the workspace root. None means the workspace manager "
            "chooses a default location."
        ),
    )
    stages: tuple[str, ...] = Field(
        default=(),
        description=(
            "Explicit stage names to run. An empty tuple means all registered stages "
            "run in their default order."
        ),
    )
    keep_workspace: bool = Field(
        default=False,
        alias="keepWorkspace",
        description="If true, do not remove the workspace directory after the build finishes.",
    )
    verbose: bool = Field(
        default=False,
        description="If true, stages produce detailed output to the configured log.",
    )


class BuildArtifact(BaseModel):
    """Metadata for one file produced during a build.

    Each artifact corresponds to a concrete file on disk within the
    build workspace. The ``path`` is relative to the workspace root.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    path: str = Field(
        description="Relative path from the workspace root to the artifact file.",
    )
    artifact_type: str = Field(
        alias="artifactType",
        description=(
            "Category of artifact. Well-known values: 'manifest', 'provenance', "
            "'log', 'version', 'layout', 'boot-config'."
        ),
    )
    checksum_sha256: str | None = Field(
        default=None,
        alias="checksumSha256",
        description="SHA-256 hex digest of the artifact file contents. None until computed.",
    )
    size_bytes: int | None = Field(
        default=None,
        alias="sizeBytes",
        ge=0,
        description="File size in bytes. None until the file is written.",
    )


class BuildManifest(BaseModel):
    """Describes the complete output of one build.

    A ``BuildManifest`` is serialised as JSON and stored in the
    workspace's metadata directory. It is the authoritative record of
    what the build produced, which stages ran, and what artifacts exist.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    manifest_version: str = Field(
        alias="manifestVersion",
        description="Version of this manifest format (e.g. 'bcs-build-manifest/v1alpha1').",
    )
    plan: BuildPlan = Field(description="The plan this build executed against.")
    artifacts: tuple[BuildArtifact, ...] = Field(
        default=(),
        description="Every artifact the build produced, in insertion order.",
    )
    stage_results: tuple[BuildStageResult, ...] = Field(
        default=(),
        alias="stageResults",
        description="Result of every stage that ran, in execution order.",
    )


class BuildWorkspace(BaseModel):
    """The directory layout of a prepared build workspace.

    All paths are absolute. Created by
    :class:`~bcs.builder.workspace.BuildWorkspaceManager` before any
    stage runs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    root: Path = Field(description="Absolute path to the workspace root directory.")
    artifacts_dir: Path = Field(
        alias="artifactsDir",
        description="Directory for produced artifacts (images, bundles).",
    )
    logs_dir: Path = Field(
        alias="logsDir",
        description="Directory for build logs and timing data.",
    )
    metadata_dir: Path = Field(
        alias="metadataDir",
        description="Directory for provenance, VERSION, and manifest files.",
    )
    cache_dir: Path = Field(
        alias="cacheDir",
        description="Directory for transient cached data (package lists, resolved references).",
    )


class BuildStageResult(BaseModel):
    """The outcome of executing one pipeline stage.

    A stage always produces a result, even on failure: ``success``
    distinguishes success from failure; ``message`` describes what
    happened; ``artifacts`` lists any files the stage produced.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    stage_name: str = Field(
        alias="stageName",
        description="Unique name of the stage that produced this result.",
    )
    success: bool = Field(
        description="True if the stage completed without error, False otherwise.",
    )
    exit_code: int = Field(
        alias="exitCode",
        ge=0,
        description=(
            "Numeric exit code for this stage. 0 means success; non-zero values "
            "follow the scheme defined in docs/BUILDER_PIPELINE.md."
        ),
    )
    message: str = Field(
        default="",
        description="Human-readable description of what the stage did or why it failed.",
    )
    elapsed_seconds: float | None = Field(
        default=None,
        alias="elapsedSeconds",
        ge=0,
        description="Wall-clock seconds the stage took to execute. None if not measured.",
    )
    artifacts: tuple[BuildArtifact, ...] = Field(
        default=(),
        description="Artifacts this stage produced, if any.",
    )


class BuildSummary(BaseModel):
    """The final outcome of an entire build invocation.

    Aggregates every stage's result into one summary object that callers
    can inspect after the pipeline completes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    plan: BuildPlan = Field(description="The plan this build ran against.")
    stage_results: tuple[BuildStageResult, ...] = Field(
        alias="stageResults",
        description="All stage results in execution order.",
    )
    success: bool = Field(
        description="True if every stage succeeded, False if any stage failed.",
    )
    elapsed_seconds: float | None = Field(
        default=None,
        alias="elapsedSeconds",
        ge=0,
        description="Total wall-clock seconds for the entire build. None if not measured.",
    )


class BuildMetadata(BaseModel):
    """Provenance metadata recorded during a build.

    This is the structured provenance record (``BLD-006``) that gets
    stored in ``metadata/provenance.json``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    build_timestamp: datetime = Field(
        alias="buildTimestamp",
        description="UTC timestamp of when the build started.",
    )
    tool_version: str = Field(
        alias="toolVersion",
        description="Version string of the bcs tool that ran the build.",
    )
    git_commit: str | None = Field(
        default=None,
        alias="gitCommit",
        description="Git commit hash of the repository at build time. None if unavailable.",
    )
    recipe_path: str = Field(
        alias="recipePath",
        description="Path to the ClassroomConfig YAML that drove this build.",
    )
    recipe_checksum: str | None = Field(
        default=None,
        alias="recipeChecksum",
        description="SHA-256 hex digest of the recipe file at build time. None if unavailable.",
    )


__all__ = [
    "BuildArtifact",
    "BuildManifest",
    "BuildMetadata",
    "BuildPlan",
    "BuildStageResult",
    "BuildSummary",
    "BuildWorkspace",
]
