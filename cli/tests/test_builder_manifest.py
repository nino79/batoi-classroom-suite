from __future__ import annotations

from pathlib import Path

import pytest

from bcs.builder.errors import ManifestError
from bcs.builder.manifest import load_manifest, save_manifest
from bcs.builder.models import BuildArtifact, BuildManifest, BuildPlan, BuildStageResult


def _make_plan(**overrides: object) -> BuildPlan:
    defaults: dict[str, object] = {"config_path": Path("/tmp/test.yaml")}
    defaults.update(overrides)
    return BuildPlan(**defaults)  # type: ignore[arg-type]


def _make_manifest() -> BuildManifest:
    plan = _make_plan()
    art = BuildArtifact(path="out.json", artifact_type="manifest")
    result = BuildStageResult(stage_name="test", success=True, exit_code=0)
    return BuildManifest(
        manifest_version="bcs-build-manifest/v1alpha1",
        plan=plan,
        artifacts=(art,),
        stage_results=(result,),
    )


def test_save_and_load_manifest(tmp_path: Path) -> None:
    manifest = _make_manifest()
    path = tmp_path / "manifest.json"
    save_manifest(manifest, path)
    assert path.is_file()

    loaded = load_manifest(path)
    assert loaded == manifest


def test_manifest_output_is_pretty_json(tmp_path: Path) -> None:
    manifest = _make_manifest()
    path = tmp_path / "manifest.json"
    save_manifest(manifest, path)
    content = path.read_text(encoding="utf-8")
    assert content.startswith("{")
    assert content.rstrip().endswith("}")
    assert '"manifestVersion"' in content


def test_load_manifest_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="Manifest file not found"):
        load_manifest(tmp_path / "nonexistent.json")


def test_load_manifest_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{invalid}", encoding="utf-8")
    with pytest.raises(ManifestError, match="not valid JSON"):
        load_manifest(path)


def test_save_manifest_creates_parent_dirs(tmp_path: Path) -> None:
    manifest = _make_manifest()
    path = tmp_path / "sub" / "nested" / "manifest.json"
    save_manifest(manifest, path)
    assert path.is_file()
    loaded = load_manifest(path)
    assert loaded == manifest


def test_manifest_round_trip_preserves_stage_results(tmp_path: Path) -> None:
    plan = _make_plan()
    results = (
        BuildStageResult(stage_name="s1", success=True, exit_code=0, elapsed_seconds=1.0),
        BuildStageResult(stage_name="s2", success=False, exit_code=1, message="fail"),
    )
    manifest = BuildManifest(manifest_version="v1", plan=plan, stage_results=results)
    path = tmp_path / "m.json"
    save_manifest(manifest, path)
    loaded = load_manifest(path)
    assert loaded.plan == plan
    assert len(loaded.stage_results) == 2
    assert loaded.stage_results[0].elapsed_seconds == 1.0
    assert loaded.stage_results[1].message == "fail"
