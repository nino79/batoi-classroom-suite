from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from bcs.builder.models import (
    BuildArtifact,
    BuildManifest,
    BuildMetadata,
    BuildPlan,
    BuildStageResult,
    BuildSummary,
    BuildWorkspace,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_plan(**overrides: object) -> BuildPlan:
    defaults: dict[str, object] = {
        "config_path": Path("/tmp/test-config.yaml"),
    }
    defaults.update(overrides)
    return BuildPlan(**defaults)  # type: ignore[arg-type]


def _make_result(**overrides: object) -> BuildStageResult:
    defaults: dict[str, object] = {
        "stage_name": "test-stage",
        "success": True,
        "exit_code": 0,
        "message": "ok",
    }
    defaults.update(overrides)
    return BuildStageResult(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# BuildPlan
# ---------------------------------------------------------------------------


def test_plan_requires_config_path() -> None:
    with pytest.raises(ValidationError):
        BuildPlan()  # type: ignore[call-arg]


def test_plan_defaults() -> None:
    plan = _make_plan()
    assert plan.workspace_root is None
    assert plan.stages == ()
    assert plan.keep_workspace is False
    assert plan.verbose is False


def test_plan_camel_case_alias() -> None:
    plan = BuildPlan(
        config_path=Path("/tmp/cfg.yaml"),
        workspaceRoot="/tmp/ws",
        keepWorkspace=True,
    )
    assert plan.config_path == Path("/tmp/cfg.yaml")
    assert plan.workspace_root == Path("/tmp/ws")
    assert plan.keep_workspace is True


def test_plan_json_alias_round_trip() -> None:
    plan = _make_plan(keep_workspace=True, stages=("validate",))
    data = plan.model_dump(mode="json", by_alias=True)
    assert data["keepWorkspace"] is True
    assert data["stages"] == ["validate"]
    assert data["workspaceRoot"] is None
    reloaded = BuildPlan.model_validate(data)
    assert reloaded == plan


def test_plan_frozen() -> None:
    plan = _make_plan()
    with pytest.raises(ValidationError):
        plan.config_path = Path("/other")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BuildArtifact
# ---------------------------------------------------------------------------


def test_artifact_requires_path_and_type() -> None:
    with pytest.raises(ValidationError):
        BuildArtifact()  # type: ignore[call-arg]


def test_artifact_defaults() -> None:
    art = BuildArtifact(path="test.json", artifact_type="manifest")
    assert art.checksum_sha256 is None
    assert art.size_bytes is None


def test_artifact_camel_case() -> None:
    art = BuildArtifact(
        path="out.img",
        artifactType="image",
        checksumSha256="abc123",
        sizeBytes=1024,
    )
    assert art.artifact_type == "image"
    assert art.checksum_sha256 == "abc123"
    assert art.size_bytes == 1024


def test_artifact_size_bytes_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        BuildArtifact(path="x", artifact_type="y", size_bytes=-1)


def test_artifact_json_round_trip() -> None:
    art = BuildArtifact(
        path="out.img", artifact_type="image", checksum_sha256="abc", size_bytes=512
    )
    data = art.model_dump(mode="json", by_alias=True)
    assert data["checksumSha256"] == "abc"
    assert data["sizeBytes"] == 512
    reloaded = BuildArtifact.model_validate(data)
    assert reloaded == art


# ---------------------------------------------------------------------------
# BuildStageResult
# ---------------------------------------------------------------------------


def test_stage_result_requires_stage_name() -> None:
    with pytest.raises(ValidationError):
        BuildStageResult(success=True, exit_code=0)  # type: ignore[call-arg]


def test_stage_result_defaults() -> None:
    result = _make_result()
    assert result.message == "ok"
    assert result.elapsed_seconds is None
    assert result.artifacts == ()


def test_stage_result_failure() -> None:
    result = _make_result(success=False, exit_code=1, message="something broke")
    assert result.success is False
    assert result.exit_code == 1


def test_stage_result_camel_case() -> None:
    result = BuildStageResult(stageName="build", success=True, exitCode=0, elapsedSeconds=1.5)
    assert result.stage_name == "build"
    assert result.elapsed_seconds == 1.5


def test_stage_result_json_round_trip() -> None:
    result = _make_result(elapsed_seconds=2.0)
    data = result.model_dump(mode="json", by_alias=True)
    assert data["elapsedSeconds"] == 2.0
    reloaded = BuildStageResult.model_validate(data)
    assert reloaded == result


# ---------------------------------------------------------------------------
# BuildManifest
# ---------------------------------------------------------------------------


def test_manifest_requires_version_and_plan() -> None:
    with pytest.raises(ValidationError):
        BuildManifest()  # type: ignore[call-arg]


def test_manifest_defaults() -> None:
    plan = _make_plan()
    manifest = BuildManifest(manifest_version="v1", plan=plan)
    assert manifest.artifacts == ()
    assert manifest.stage_results == ()


def test_manifest_with_artifacts_and_results() -> None:
    plan = _make_plan()
    art = BuildArtifact(path="out.json", artifact_type="manifest")
    result = _make_result()
    manifest = BuildManifest(
        manifest_version="v1",
        plan=plan,
        artifacts=(art,),
        stage_results=(result,),
    )
    assert len(manifest.artifacts) == 1
    assert len(manifest.stage_results) == 1


def test_manifest_json_round_trip() -> None:
    plan = _make_plan()
    art = BuildArtifact(path="out.json", artifact_type="manifest")
    result = _make_result(elapsed_seconds=0.5)
    manifest = BuildManifest(
        manifest_version="bcs-build-manifest/v1alpha1",
        plan=plan,
        artifacts=(art,),
        stage_results=(result,),
    )
    data = manifest.model_dump(mode="json", by_alias=True)
    assert data["manifestVersion"] == "bcs-build-manifest/v1alpha1"
    assert len(data["artifacts"]) == 1
    assert len(data["stageResults"]) == 1
    reloaded = BuildManifest.model_validate(data)
    assert reloaded == manifest


# ---------------------------------------------------------------------------
# BuildWorkspace
# ---------------------------------------------------------------------------


def test_workspace_requires_all_paths() -> None:
    with pytest.raises(ValidationError):
        BuildWorkspace()  # type: ignore[call-arg]


def test_workspace_construction() -> None:
    ws = BuildWorkspace(
        root=Path("/ws"),
        artifacts_dir=Path("/ws/artifacts"),
        logs_dir=Path("/ws/logs"),
        metadata_dir=Path("/ws/metadata"),
        cache_dir=Path("/ws/cache"),
    )
    assert ws.root == Path("/ws")
    assert ws.artifacts_dir == Path("/ws/artifacts")


def test_workspace_camel_case() -> None:
    ws = BuildWorkspace(
        root=Path("/ws"),
        artifactsDir=Path("/ws/artifacts"),
        logsDir=Path("/ws/logs"),
        metadataDir=Path("/ws/metadata"),
        cacheDir=Path("/ws/cache"),
    )
    assert ws.artifacts_dir == Path("/ws/artifacts")
    assert ws.metadata_dir == Path("/ws/metadata")


def test_workspace_json_round_trip() -> None:
    ws = BuildWorkspace(
        root=Path("/root"),
        artifacts_dir=Path("/root/artifacts"),
        logs_dir=Path("/root/logs"),
        metadata_dir=Path("/root/metadata"),
        cache_dir=Path("/root/cache"),
    )
    data = ws.model_dump(mode="json", by_alias=True)
    reloaded = BuildWorkspace.model_validate(data)
    assert reloaded == ws


# ---------------------------------------------------------------------------
# BuildSummary
# ---------------------------------------------------------------------------


def test_summary_requires_plan_and_success() -> None:
    with pytest.raises(ValidationError):
        BuildSummary()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BuildSummary(plan=_make_plan())  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BuildSummary(success=True)  # type: ignore[call-arg]


def test_summary_construction() -> None:
    plan = _make_plan()
    results = (_make_result(), _make_result())
    summary = BuildSummary(plan=plan, stage_results=results, success=True)
    assert summary.success is True
    assert summary.elapsed_seconds is None


def test_summary_with_failure() -> None:
    plan = _make_plan()
    results = (_make_result(success=True), _make_result(success=False, exit_code=1))
    summary = BuildSummary(plan=plan, stage_results=results, success=False)
    assert summary.success is False


def test_summary_json_round_trip() -> None:
    plan = _make_plan()
    results = (_make_result(elapsed_seconds=1.0),)
    summary = BuildSummary(plan=plan, stage_results=results, success=True, elapsed_seconds=1.0)
    data = summary.model_dump(mode="json", by_alias=True)
    reloaded = BuildSummary.model_validate(data)
    assert reloaded == summary


def test_summary_elapsed_seconds_non_negative() -> None:
    with pytest.raises(ValidationError):
        BuildSummary(
            plan=_make_plan(),
            stage_results=(_make_result(),),
            success=True,
            elapsed_seconds=-1,
        )


# ---------------------------------------------------------------------------
# BuildMetadata
# ---------------------------------------------------------------------------


def test_metadata_requires_required_fields() -> None:
    with pytest.raises(ValidationError):
        BuildMetadata()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BuildMetadata(tool_version="1.0", recipe_path="cfg.yaml")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BuildMetadata(build_timestamp=datetime.now(UTC), recipe_path="cfg.yaml")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BuildMetadata(build_timestamp=datetime.now(UTC), tool_version="1.0")  # type: ignore[call-arg]


def test_metadata_construction() -> None:
    ts = datetime(2026, 7, 9, 12, 0, 0, tzinfo=UTC)
    meta = BuildMetadata(build_timestamp=ts, tool_version="0.1.0", recipe_path="/tmp/cfg.yaml")
    assert meta.build_timestamp == ts
    assert meta.tool_version == "0.1.0"
    assert meta.recipe_path == "/tmp/cfg.yaml"
    assert meta.git_commit is None
    assert meta.recipe_checksum is None


def test_metadata_camel_case() -> None:
    meta = BuildMetadata(
        buildTimestamp="2026-07-09T12:00:00Z",
        toolVersion="1.0",
        recipePath="/cfg.yaml",
        gitCommit="abc123",
        recipeChecksum="def456",
    )
    assert meta.tool_version == "1.0"
    assert meta.git_commit == "abc123"
    assert meta.recipe_checksum == "def456"


def test_metadata_json_round_trip() -> None:
    ts = datetime(2026, 7, 9, 12, 0, 0, tzinfo=UTC)
    meta = BuildMetadata(
        build_timestamp=ts,
        tool_version="0.1.0",
        recipe_path="/tmp/cfg.yaml",
        git_commit="abc",
        recipe_checksum="def",
    )
    data = meta.model_dump(mode="json", by_alias=True)
    reloaded = BuildMetadata.model_validate(data)
    assert reloaded == meta


def test_hashable_models() -> None:
    plan = _make_plan()
    assert isinstance(hash(plan), int)
    art = BuildArtifact(path="x", artifact_type="y")
    assert isinstance(hash(art), int)
    result = _make_result()
    assert isinstance(hash(result), int)
    manifest = BuildManifest(manifest_version="v1", plan=plan)
    assert isinstance(hash(manifest), int)
