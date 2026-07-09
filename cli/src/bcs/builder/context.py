"""Mutable container that carries state through the build pipeline.

``BuildContext`` is the single object passed through every stage of
the pipeline. Stages read from it (plan, workspace) and write to it
(results, metadata). It is deliberately **mutable**: unlike
``bcs.context.RuntimeContext`` (which is frozen because it is built
once at startup), ``BuildContext`` accumulates state as the pipeline
progresses.

Stage implementations should treat ``BuildContext`` as an append-only
accumulator - they may append to ``stage_results`` and ``artifacts``,
set ``metadata``, and read from ``plan`` and ``workspace``, but should
not overwrite fields set by earlier stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bcs.builder.models import (
    BuildArtifact,
    BuildMetadata,
    BuildPlan,
    BuildStageResult,
    BuildWorkspace,
)


@dataclass
class BuildContext:
    """Holds all state for one build invocation.

    Attributes:
        plan: The resolved build plan. Set at construction and never
            changed.
        workspace: The prepared workspace layout. Set by
            :class:`~bcs.builder.stages.PrepareWorkspaceStage` and read
            by every subsequent stage.
        metadata: Provenance metadata. Set by
            :class:`~bcs.builder.stages.FinalizeStage`.
        stage_results: Ordered list of results from every stage that ran.
            Appended to by each stage on completion.
        artifacts: Cumulative list of every artifact produced across all
            stages. Appended to by stages that produce files.
    """

    plan: BuildPlan
    workspace: BuildWorkspace | None = None
    metadata: BuildMetadata | None = None
    stage_results: list[BuildStageResult] = field(default_factory=list)
    artifacts: list[BuildArtifact] = field(default_factory=list)


__all__ = ["BuildContext"]
