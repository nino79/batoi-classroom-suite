"""Protocol definitions for the Builder pipeline.

The central protocol is :class:`BuildStage`: any object that implements
it can be registered with :class:`~bcs.builder.pipeline.BuildPipeline`.
The protocol uses structural subtyping (``@runtime_checkable``),
matching the convention established by
:class:`bcs.platform.execution.CommandRunner`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bcs.builder.context import BuildContext
from bcs.builder.models import BuildStageResult


@runtime_checkable
class BuildStage(Protocol):
    """A single, independently invocable step in the build pipeline.

    Every stage has a ``name`` (used for selection via
    ``BuildPlan.stages``) and a ``run`` method that receives the shared
    :class:`BuildContext` and returns a :class:`BuildStageResult`.

    Stages should be **idempotent** when called with the same context:
    running the same stage twice on the same workspace should produce
    the same files and results.
    """

    @property
    def name(self) -> str:
        """Unique stage name (e.g. ``"validate-config"``, ``"prepare-workspace"``)."""
        ...

    def run(self, context: BuildContext) -> BuildStageResult:
        """Execute this stage and return its result.

        Args:
            context: The shared build context. Stage implementations
                should read from ``context.plan`` and
                ``context.workspace``, and may append to
                ``context.stage_results`` and ``context.artifacts``.

        Returns:
            A :class:`BuildStageResult` summarising the outcome.

        Raises:
            BuilderError: Subclasses for domain-specific failures.
        """
        ...


__all__ = ["BuildStage"]
