from __future__ import annotations

from bcs.builder.errors import (
    ArtifactError,
    BuilderError,
    ManifestError,
    PipelineError,
    ValidationError,
    WorkspaceError,
)


def test_builder_error_is_base() -> None:
    exc = BuilderError("base error")
    assert exc.message == "base error"
    assert exc.details == {}


def test_builder_error_with_details() -> None:
    exc = BuilderError("detailed", details={"key": "value"})
    assert exc.details == {"key": "value"}


def test_workspace_error_inherits() -> None:
    exc = WorkspaceError("workspace error")
    assert isinstance(exc, BuilderError)
    assert exc.message == "workspace error"


def test_manifest_error_inherits() -> None:
    exc = ManifestError("manifest error")
    assert isinstance(exc, BuilderError)
    assert exc.message == "manifest error"


def test_pipeline_error_inherits() -> None:
    exc = PipelineError("pipeline error")
    assert isinstance(exc, BuilderError)
    assert exc.message == "pipeline error"


def test_validation_error_inherits() -> None:
    exc = ValidationError("validation error")
    assert isinstance(exc, BuilderError)
    assert exc.message == "validation error"


def test_artifact_error_inherits() -> None:
    exc = ArtifactError("artifact error")
    assert isinstance(exc, BuilderError)
    assert exc.message == "artifact error"


def test_all_errors_carry_details() -> None:
    details = {"path": "/some/path", "code": 42}
    for exc_type in (WorkspaceError, ManifestError, PipelineError, ValidationError, ArtifactError):
        exc = exc_type("test", details=details)
        assert exc.details == details, f"{exc_type.__name__} does not carry details"
