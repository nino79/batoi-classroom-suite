from __future__ import annotations

from pathlib import Path

from bcs.builder.context import BuildContext
from bcs.builder.models import BuildPlan, BuildStageResult
from bcs.builder.protocols import BuildStage


def test_build_stage_is_a_protocol() -> None:
    # Protocol classes have a _is_protocol attribute set to True
    assert hasattr(BuildStage, "_is_protocol")


def test_class_matching_protocol() -> None:
    """Classes with name property and run method should match the protocol."""

    class MyStage:
        @property
        def name(self) -> str:
            return "my-stage"

        def run(self, context: BuildContext) -> BuildStageResult:
            return BuildStageResult(stage_name=self.name, success=True, exit_code=0)

    stage = MyStage()
    assert isinstance(stage, BuildStage)


def test_function_based_stage() -> None:
    """A module-level function shouldn't match (no name property)."""

    def my_run(context: BuildContext) -> BuildStageResult:
        return BuildStageResult(stage_name="fn", success=True, exit_code=0)

    # Plain functions don't have a name property
    assert not isinstance(my_run, BuildStage)


def test_protocol_accepts_any_context() -> None:
    plan = BuildPlan(config_path=Path("/tmp/test.yaml"))
    context = BuildContext(plan=plan)

    class SimpleStage:
        @property
        def name(self) -> str:
            return "simple"

        def run(self, context: BuildContext) -> BuildStageResult:
            return BuildStageResult(stage_name=self.name, success=True, exit_code=0)

    stage = SimpleStage()
    assert isinstance(stage, BuildStage)
    result = stage.run(context)
    assert result.success
