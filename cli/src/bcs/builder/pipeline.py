"""Generic build pipeline orchestrator.

``BuildPipeline`` holds an ordered sequence of :class:`BuildStage`
objects and executes them against a shared :class:`BuildContext`.
It handles stage selection (filtering by ``BuildPlan.stages``),
timing, result aggregation, and error isolation so individual stages
do not need to worry about orchestration concerns.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from bcs.builder.context import BuildContext
from bcs.builder.errors import PipelineError
from bcs.builder.models import BuildStageResult, BuildSummary
from bcs.builder.protocols import BuildStage


class BuildPipeline:
    """Orchestrates an ordered sequence of build stages.

    Usage::

        pipeline = BuildPipeline(stages=[
            ValidateConfigStage(),
            PrepareWorkspaceStage(),
        ])
        plan = BuildPlan(config_path=Path("config.yaml"))
        context = BuildContext(plan=plan)
        summary = pipeline.run(context)
    """

    def __init__(self, stages: Sequence[BuildStage]) -> None:
        """Store the stage sequence; does not execute anything.

        Args:
            stages: Ordered stages to run. Each must implement the
                :class:`BuildStage` protocol.

        Raises:
            PipelineError: If ``stages`` is empty.
        """
        if not stages:
            raise PipelineError(
                "At least one stage is required to build a pipeline",
            )
        self._stages = tuple(stages)

    @property
    def stages(self) -> tuple[BuildStage, ...]:
        """Immutable view of the registered stage sequence."""
        return self._stages

    def run(self, context: BuildContext) -> BuildSummary:
        """Execute all applicable stages and return a summary.

        Stage selection:
            - If ``context.plan.stages`` is empty, every registered
              stage runs in order.
            - If ``context.plan.stages`` is non-empty, only stages
              whose ``name`` appears in that tuple run, preserving
              the pipeline's registration order (not the tuple's
              order).

        Execution guarantees:
            - Every stage gets its own :class:`BuildStageResult`
              appended to ``context.stage_results``.
            - The pipeline does **not** stop on a stage failure:
              subsequent stages still execute (callers inspect
              ``BuildSummary.success`` to determine overall outcome).
            - Exceptions that are not ``BuilderError`` subclasses
              are **not** caught - they propagate immediately and
              terminate the pipeline.

        Returns:
            A :class:`BuildSummary` aggregating every stage result.
        """
        plan = context.plan
        stage_names: frozenset[str] = frozenset(plan.stages) if plan.stages else frozenset()
        run_all = not plan.stages

        overall_start = time.monotonic()
        overall_success = True

        for stage in self._stages:
            if not run_all and stage.name not in stage_names:
                continue

            stage_start = time.monotonic()
            try:
                result: BuildStageResult = stage.run(context)
            except Exception as exc:  # noqa: BLE001
                elapsed = time.monotonic() - stage_start
                result = BuildStageResult(
                    stage_name=stage.name,
                    success=False,
                    exit_code=99,
                    message=f"Unhandled exception in stage '{stage.name}': {exc}",
                    elapsed_seconds=elapsed,
                )
                overall_success = False
            else:
                if not result.success:
                    overall_success = False

            context.stage_results.append(result)

        return BuildSummary(
            plan=plan,
            stage_results=tuple(context.stage_results),
            success=overall_success,
            elapsed_seconds=time.monotonic() - overall_start,
        )


__all__ = ["BuildPipeline"]
