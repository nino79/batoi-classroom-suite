"""The Builder subsystem: pipeline orchestration for golden-image creation.

This package provides the core infrastructure for the Builder subsystem
- pipeline orchestration, workspace management, manifest handling, and
stage execution. It does **not** implement image creation, Clonezilla
integration, or Deploy interaction; see ``docs/BUILDER_PIPELINE.md``
for the full design and ``docs/architecture/builder.md`` for the
architecture rationale.

Every public symbol is re-exported here so consumers import from
``bcs.builder`` rather than from individual submodules.
"""

from bcs.builder.context import BuildContext
from bcs.builder.errors import (
    ArtifactError,
    BuilderError,
    ManifestError,
    PipelineError,
    ValidationError,
    WorkspaceError,
)
from bcs.builder.execution import (
    compute_file_checksum,
    copy_file,
    ensure_directory,
    read_json,
    write_json,
)
from bcs.builder.manifest import load_manifest, save_manifest
from bcs.builder.models import (
    BuildArtifact,
    BuildManifest,
    BuildMetadata,
    BuildPlan,
    BuildStageResult,
    BuildSummary,
    BuildWorkspace,
)
from bcs.builder.pipeline import BuildPipeline
from bcs.builder.protocols import BuildStage
from bcs.builder.stages import (
    FinalizeStage,
    GenerateManifestStage,
    PrepareWorkspaceStage,
    ValidateConfigStage,
)
from bcs.builder.workspace import BuildWorkspaceManager

__all__ = [
    "ArtifactError",
    "BuildArtifact",
    "BuildContext",
    "BuildManifest",
    "BuildMetadata",
    "BuildPipeline",
    "BuildPlan",
    "BuildStage",
    "BuildStageResult",
    "BuildSummary",
    "BuildWorkspace",
    "BuildWorkspaceManager",
    "BuilderError",
    "FinalizeStage",
    "GenerateManifestStage",
    "ManifestError",
    "PipelineError",
    "PrepareWorkspaceStage",
    "ValidateConfigStage",
    "ValidationError",
    "WorkspaceError",
    "compute_file_checksum",
    "copy_file",
    "ensure_directory",
    "load_manifest",
    "read_json",
    "save_manifest",
    "write_json",
]
