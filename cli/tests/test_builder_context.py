from __future__ import annotations

from pathlib import Path

from bcs.builder.context import BuildContext
from bcs.builder.models import (
    BuildArtifact,
    BuildMetadata,
    BuildPlan,
    BuildStageResult,
    BuildWorkspace,
)


def _make_plan(**overrides: object) -> BuildPlan:
    defaults: dict[str, object] = {"config_path": Path("/tmp/test.yaml")}
    defaults.update(overrides)
    return BuildPlan(**defaults)  # type: ignore[arg-type]


def _make_workspace() -> BuildWorkspace:
    return BuildWorkspace(
        root=Path("/ws"),
        artifacts_dir=Path("/ws/artifacts"),
        logs_dir=Path("/ws/logs"),
        metadata_dir=Path("/ws/metadata"),
        cache_dir=Path("/ws/cache"),
    )


def test_context_requires_plan() -> None:
    plan = _make_plan()
    ctx = BuildContext(plan=plan)
    assert ctx.plan == plan
    assert ctx.workspace is None
    assert ctx.metadata is None
    assert ctx.stage_results == []
    assert ctx.artifacts == []


def test_context_accumulates_stage_results() -> None:
    ctx = BuildContext(plan=_make_plan())
    r1 = BuildStageResult(stage_name="a", success=True, exit_code=0)
    r2 = BuildStageResult(stage_name="b", success=False, exit_code=1)
    ctx.stage_results.append(r1)
    ctx.stage_results.append(r2)
    assert len(ctx.stage_results) == 2
    assert ctx.stage_results[0].stage_name == "a"
    assert ctx.stage_results[1].stage_name == "b"


def test_context_accumulates_artifacts() -> None:
    ctx = BuildContext(plan=_make_plan())
    a1 = BuildArtifact(path="out.json", artifact_type="manifest")
    a2 = BuildArtifact(path="provenance.json", artifact_type="provenance")
    ctx.artifacts.append(a1)
    ctx.artifacts.append(a2)
    assert len(ctx.artifacts) == 2


def test_context_can_set_workspace() -> None:
    ctx = BuildContext(plan=_make_plan())
    ws = _make_workspace()
    ctx.workspace = ws
    assert ctx.workspace is not None
    assert ctx.workspace.root == Path("/ws")


def test_context_can_set_metadata() -> None:
    ctx = BuildContext(plan=_make_plan())
    from datetime import UTC, datetime

    meta = BuildMetadata(
        build_timestamp=datetime.now(UTC),
        tool_version="1.0",
        recipe_path="/cfg.yaml",
    )
    ctx.metadata = meta
    assert ctx.metadata is not None
    assert ctx.metadata.tool_version == "1.0"


def test_context_mutable() -> None:
    """BuildContext is deliberately mutable - verify we can change fields."""
    ctx = BuildContext(plan=_make_plan())
    ctx.workspace = _make_workspace()
    ctx.stage_results.append(BuildStageResult(stage_name="s1", success=True, exit_code=0))
    ctx.stage_results.append(BuildStageResult(stage_name="s2", success=True, exit_code=0))
    assert len(ctx.stage_results) == 2
