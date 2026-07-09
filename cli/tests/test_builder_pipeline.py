from __future__ import annotations

from pathlib import Path

import pytest

from bcs.builder.context import BuildContext
from bcs.builder.errors import PipelineError
from bcs.builder.models import BuildPlan, BuildStageResult
from bcs.builder.pipeline import BuildPipeline
from bcs.builder.stages import (
    FinalizeStage,
    GenerateManifestStage,
    PrepareWorkspaceStage,
    ValidateConfigStage,
)


def _make_plan(**overrides: object) -> BuildPlan:
    defaults: dict[str, object] = {"config_path": Path("/tmp/test.yaml")}
    defaults.update(overrides)
    return BuildPlan(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_pipeline_requires_at_least_one_stage() -> None:
    with pytest.raises(PipelineError, match="At least one stage"):
        BuildPipeline(stages=[])


def test_pipeline_stages_property() -> None:
    stages = [ValidateConfigStage(), PrepareWorkspaceStage()]
    pipeline = BuildPipeline(stages=stages)
    assert len(pipeline.stages) == 2
    assert pipeline.stages[0].name == "validate-config"
    assert pipeline.stages[1].name == "prepare-workspace"


# ---------------------------------------------------------------------------
# Run all stages
# ---------------------------------------------------------------------------


def test_pipeline_runs_all_stages_in_order(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("dummy", encoding="utf-8")
    ws_root = tmp_path / "ws"

    plan = _make_plan(config_path=config_path, workspace_root=ws_root, keep_workspace=True)
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
            GenerateManifestStage(),
            FinalizeStage(),
        ]
    )
    summary = pipeline.run(ctx)

    assert summary.success
    assert len(summary.stage_results) == 4
    assert summary.stage_results[0].stage_name == "validate-config"
    assert summary.stage_results[1].stage_name == "prepare-workspace"
    assert summary.stage_results[2].stage_name == "generate-manifest"
    assert summary.stage_results[3].stage_name == "finalize"
    assert summary.elapsed_seconds is not None
    assert summary.elapsed_seconds >= 0


def test_pipeline_failure_in_stage(tmp_path: Path) -> None:
    """Pipeline should not stop on stage failure - all stages run."""
    config_path = tmp_path / "config.txt"  # wrong extension -> fails validation
    config_path.write_text("dummy", encoding="utf-8")
    ws_root = tmp_path / "ws"

    plan = _make_plan(config_path=config_path, workspace_root=ws_root, keep_workspace=True)
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
            FinalizeStage(),
        ]
    )
    summary = pipeline.run(ctx)

    assert not summary.success
    # validate-config should fail
    assert not summary.stage_results[0].success
    # But all stages still ran
    assert len(summary.stage_results) == 3


# ---------------------------------------------------------------------------
# Stage selection
# ---------------------------------------------------------------------------


def test_pipeline_selects_specific_stages(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("dummy", encoding="utf-8")
    ws_root = tmp_path / "ws"

    plan = _make_plan(
        config_path=config_path,
        workspace_root=ws_root,
        stages=("prepare-workspace", "finalize"),
    )
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
            GenerateManifestStage(),
            FinalizeStage(),
        ]
    )
    summary = pipeline.run(ctx)

    assert len(summary.stage_results) == 2
    assert summary.stage_results[0].stage_name == "prepare-workspace"
    assert summary.stage_results[1].stage_name == "finalize"


def test_pipeline_selects_single_stage(tmp_path: Path) -> None:
    plan = _make_plan(stages=("validate-config",))
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
        ]
    )
    summary = pipeline.run(ctx)

    assert len(summary.stage_results) == 1
    assert summary.stage_results[0].stage_name == "validate-config"


def test_pipeline_preserves_registration_order(tmp_path: Path) -> None:
    """When stages are selected by name, they run in registration order,
    not in the order specified by BuildPlan.stages."""
    plan = _make_plan(stages=("prepare-workspace", "validate-config"))
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
        ]
    )
    summary = pipeline.run(ctx)

    assert len(summary.stage_results) == 2
    # Registration order: validate-config first, even though plan listed
    # prepare-workspace first
    assert summary.stage_results[0].stage_name == "validate-config"
    assert summary.stage_results[1].stage_name == "prepare-workspace"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_pipeline_recovers_from_failure(tmp_path: Path) -> None:
    """A failing stage should not prevent other stages from running."""

    class FailStage:
        @property
        def name(self) -> str:
            return "fail-stage"

        def run(self, context: BuildContext) -> BuildStageResult:
            return BuildStageResult(
                stage_name="fail-stage", success=False, exit_code=99, message="boom"
            )

    config_path = tmp_path / "config.yaml"
    config_path.write_text("dummy", encoding="utf-8")
    plan = _make_plan(config_path=config_path, workspace_root=tmp_path / "ws", keep_workspace=True)
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            FailStage(),
            PrepareWorkspaceStage(),
        ]
    )
    summary = pipeline.run(ctx)
    assert not summary.success
    assert not summary.stage_results[0].success
    assert summary.stage_results[1].success  # second stage still ran


def test_pipeline_catches_exception_in_stage(tmp_path: Path) -> None:
    """An exception in a stage should not crash the pipeline."""

    class ExplodingStage:
        @property
        def name(self) -> str:
            return "explode"

        def run(self, context: BuildContext) -> BuildStageResult:
            msg = "internal error"
            raise RuntimeError(msg)

    plan = _make_plan(config_path=tmp_path / "c.yaml")
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ExplodingStage(),
            ValidateConfigStage(),
        ]
    )
    summary = pipeline.run(ctx)
    assert not summary.success
    assert not summary.stage_results[0].success
    assert summary.stage_results[0].exit_code == 99  # generic error code
    assert "Unhandled exception" in summary.stage_results[0].message


# ---------------------------------------------------------------------------
# Integration: full pipeline
# ---------------------------------------------------------------------------


def test_full_pipeline_success(tmp_path: Path) -> None:
    config_path = tmp_path / "classroom.yaml"
    config_path.write_text("dummy", encoding="utf-8")
    ws_root = tmp_path / "build"

    plan = _make_plan(
        config_path=config_path,
        workspace_root=ws_root,
        keep_workspace=True,
    )
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
            GenerateManifestStage(),
            FinalizeStage(),
        ]
    )
    summary = pipeline.run(ctx)

    assert summary.success
    assert ws_root.is_dir()  # kept because keep_workspace=True
    # Check files were created
    assert (ws_root / "metadata" / "manifest.json").is_file()
    assert (ws_root / "metadata" / "provenance.json").is_file()
    assert (ws_root / "logs" / "build.log").is_file()


def test_full_pipeline_with_cleanup(tmp_path: Path) -> None:
    config_path = tmp_path / "classroom.yaml"
    config_path.write_text("dummy", encoding="utf-8")
    ws_root = tmp_path / "build"

    plan = _make_plan(
        config_path=config_path,
        workspace_root=ws_root,
        keep_workspace=False,
    )
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
            GenerateManifestStage(),
            FinalizeStage(),
        ]
    )
    summary = pipeline.run(ctx)

    assert summary.success
    assert not ws_root.exists()  # workspace was cleaned


def test_pipeline_empty_stages_means_all(tmp_path: Path) -> None:
    """Empty plan.stages should run every registered stage."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("dummy", encoding="utf-8")
    plan = _make_plan(config_path=config_path, workspace_root=tmp_path / "ws", keep_workspace=True)
    ctx = BuildContext(plan=plan)

    pipeline = BuildPipeline(
        stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
        ]
    )
    summary = pipeline.run(ctx)
    assert len(summary.stage_results) == 2
