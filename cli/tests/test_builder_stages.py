from __future__ import annotations

from pathlib import Path

from bcs.builder.context import BuildContext
from bcs.builder.models import BuildPlan
from bcs.builder.stages import (
    FinalizeStage,
    GenerateManifestStage,
    PrepareWorkspaceStage,
    ValidateConfigStage,
)


def _make_plan(**overrides: object) -> BuildPlan:
    defaults: dict[str, object] = {"config_path": Path("/tmp/test-config.yaml")}
    defaults.update(overrides)
    return BuildPlan(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ValidateConfigStage
# ---------------------------------------------------------------------------


def test_validate_config_rejects_nonexistent(tmp_path: Path) -> None:
    plan = _make_plan(config_path=tmp_path / "nonexistent.yaml")
    ctx = BuildContext(plan=plan)
    stage = ValidateConfigStage()
    result = stage.run(ctx)
    assert not result.success
    assert result.exit_code == 1
    assert "does not exist" in result.message


def test_validate_config_rejects_directory(tmp_path: Path) -> None:
    plan = _make_plan(config_path=tmp_path)
    ctx = BuildContext(plan=plan)
    stage = ValidateConfigStage()
    result = stage.run(ctx)
    assert not result.success
    assert "not a regular file" in result.message


def test_validate_config_rejects_wrong_extension(tmp_path: Path) -> None:
    config_path = tmp_path / "config.txt"
    config_path.write_text("dummy", encoding="utf-8")
    plan = _make_plan(config_path=config_path)
    ctx = BuildContext(plan=plan)
    stage = ValidateConfigStage()
    result = stage.run(ctx)
    assert not result.success
    assert ".yaml or .yml" in result.message


def test_validate_config_accepts_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("dummy", encoding="utf-8")
    plan = _make_plan(config_path=config_path)
    ctx = BuildContext(plan=plan)
    stage = ValidateConfigStage()
    result = stage.run(ctx)
    assert result.success
    assert result.exit_code == 0


def test_validate_config_accepts_yml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text("dummy", encoding="utf-8")
    plan = _make_plan(config_path=config_path)
    ctx = BuildContext(plan=plan)
    stage = ValidateConfigStage()
    result = stage.run(ctx)
    assert result.success


def test_validate_config_name_property() -> None:
    stage = ValidateConfigStage()
    assert stage.name == "validate-config"


# ---------------------------------------------------------------------------
# PrepareWorkspaceStage
# ---------------------------------------------------------------------------


def test_prepare_workspace_creates_directories(tmp_path: Path) -> None:
    ws_root = tmp_path / "workspace"
    plan = _make_plan(workspace_root=ws_root)
    ctx = BuildContext(plan=plan)
    stage = PrepareWorkspaceStage()
    result = stage.run(ctx)
    assert result.success
    assert result.exit_code == 0
    assert ctx.workspace is not None
    assert ctx.workspace.root == ws_root
    assert ctx.workspace.artifacts_dir.is_dir()
    assert ctx.workspace.logs_dir.is_dir()
    assert ctx.workspace.metadata_dir.is_dir()
    assert ctx.workspace.cache_dir.is_dir()


def test_prepare_workspace_default_root(tmp_path: Path) -> None:
    plan = _make_plan(workspace_root=None)
    ctx = BuildContext(plan=plan)
    stage = PrepareWorkspaceStage()
    result = stage.run(ctx)
    assert result.success
    assert ctx.workspace is not None
    # Default root should be in CWD with .bcs-build- prefix
    assert ".bcs-build-" in str(ctx.workspace.root)


def test_prepare_workspace_name_property() -> None:
    stage = PrepareWorkspaceStage()
    assert stage.name == "prepare-workspace"


# ---------------------------------------------------------------------------
# GenerateManifestStage
# ---------------------------------------------------------------------------


def test_generate_manifest_without_workspace_fails(tmp_path: Path) -> None:
    plan = _make_plan()
    ctx = BuildContext(plan=plan)
    stage = GenerateManifestStage()
    result = stage.run(ctx)
    assert not result.success
    assert "workspace has not been prepared" in result.message


def test_generate_manifest_writes_file(tmp_path: Path) -> None:
    from bcs.builder.stages import PrepareWorkspaceStage

    plan = _make_plan(workspace_root=tmp_path / "ws")
    ctx = BuildContext(plan=plan)

    # Prepare workspace first
    prepare = PrepareWorkspaceStage()
    prepare.run(ctx)
    assert ctx.workspace is not None

    stage = GenerateManifestStage()
    result = stage.run(ctx)
    assert result.success
    assert result.exit_code == 0

    manifest_path = ctx.workspace.metadata_dir / "manifest.json"
    assert manifest_path.is_file()
    assert len(ctx.artifacts) >= 1
    assert any(a.path == "metadata/manifest.json" for a in ctx.artifacts)


def test_generate_manifest_name_property() -> None:
    stage = GenerateManifestStage()
    assert stage.name == "generate-manifest"


# ---------------------------------------------------------------------------
# FinalizeStage
# ---------------------------------------------------------------------------


def test_finalize_without_workspace_fails(tmp_path: Path) -> None:
    plan = _make_plan()
    ctx = BuildContext(plan=plan)
    stage = FinalizeStage()
    result = stage.run(ctx)
    assert not result.success
    assert "workspace has not been prepared" in result.message


def test_finalize_writes_provenance_and_log(tmp_path: Path) -> None:
    from bcs.builder.stages import PrepareWorkspaceStage

    plan = _make_plan(workspace_root=tmp_path / "ws", keep_workspace=True)
    ctx = BuildContext(plan=plan)

    prepare = PrepareWorkspaceStage()
    prepare.run(ctx)
    assert ctx.workspace is not None

    stage = FinalizeStage()
    result = stage.run(ctx)
    assert result.success

    provenance_path = ctx.workspace.metadata_dir / "provenance.json"
    assert provenance_path.is_file()

    log_path = ctx.workspace.logs_dir / "build.log"
    assert log_path.is_file()

    assert ctx.metadata is not None
    assert ctx.metadata.tool_version is not None
    assert ctx.metadata.recipe_path == str(plan.config_path)


def test_finalize_cleans_workspace_when_not_kept(tmp_path: Path) -> None:
    from bcs.builder.stages import PrepareWorkspaceStage

    plan = _make_plan(workspace_root=tmp_path / "ws", keep_workspace=False)
    ctx = BuildContext(plan=plan)

    prepare = PrepareWorkspaceStage()
    prepare.run(ctx)
    assert ctx.workspace is not None
    ws_root = ctx.workspace.root

    stage = FinalizeStage()
    result = stage.run(ctx)
    assert result.success
    # Workspace should be cleaned (deleted)
    assert not ws_root.exists()


def test_finalize_keeps_workspace_when_requested(tmp_path: Path) -> None:
    from bcs.builder.stages import PrepareWorkspaceStage

    plan = _make_plan(workspace_root=tmp_path / "ws", keep_workspace=True)
    ctx = BuildContext(plan=plan)

    prepare = PrepareWorkspaceStage()
    prepare.run(ctx)
    assert ctx.workspace is not None
    ws_root = ctx.workspace.root

    stage = FinalizeStage()
    result = stage.run(ctx)
    assert result.success
    assert ws_root.exists()


def test_finalize_name_property() -> None:
    stage = FinalizeStage()
    assert stage.name == "finalize"


# ---------------------------------------------------------------------------
# All stages satisfy protocol
# ---------------------------------------------------------------------------


def test_all_stages_satisfy_build_stage_protocol() -> None:
    from bcs.builder.protocols import BuildStage

    stages = [
        ValidateConfigStage(),
        PrepareWorkspaceStage(),
        GenerateManifestStage(),
        FinalizeStage(),
    ]
    for stage in stages:
        assert isinstance(stage, BuildStage), f"{stage.name} does not satisfy BuildStage"
