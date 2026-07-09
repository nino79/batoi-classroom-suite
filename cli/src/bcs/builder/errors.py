"""Exception hierarchy for the Builder subsystem.

``BuilderError`` is the base for every error the Builder raises
intentionally. It is deliberately independent of
``bcs.platform.errors.PlatformError`` (which is for OS-process-level
failures) and ``bcs.errors.BcsError`` (which is CLI-adapter-level):
the Builder is core infrastructure between those two layers.

All subclasses accept a ``message`` and optional ``details`` dict for
structured error reporting.
"""

from __future__ import annotations


class BuilderError(Exception):
    """Base class for every Builder error.

    Never raised directly; always one of the subclasses below.
    """

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class WorkspaceError(BuilderError):
    """Raised when a workspace operation fails.

    Examples: directory creation fails, path is not writable, cleanup
    encounters a permission error.
    """


class ManifestError(BuilderError):
    """Raised when a manifest read or write operation fails.

    Examples: file is not valid JSON, schema version mismatch, required
    field missing on deserialization.
    """


class PipelineError(BuilderError):
    """Raised when the pipeline encounters an orchestration error.

    Examples: a stage is unknown, stage execution order is violated,
    the pipeline is stopped mid-execution.
    """


class ValidationError(BuilderError):
    """Raised when configuration or plan validation fails.

    Examples: config file not found, required field missing, semantic
    inconsistency in the build plan.
    """


class ArtifactError(BuilderError):
    """Raised when artifact production or verification fails.

    Examples: checksum mismatch, output path not writable, artifact
    file is unexpectedly empty.
    """


__all__ = [
    "ArtifactError",
    "BuilderError",
    "ManifestError",
    "PipelineError",
    "ValidationError",
    "WorkspaceError",
]
