# Architecture Decision Records (ADRs)

This directory records the significant, hard-to-reverse decisions behind Batoi Classroom Suite's design — the *why*, not just the *what*. `ARCHITECTURE.md` and `SPECIFICATION.md` describe the current state; ADRs preserve the reasoning and alternatives behind how that state came to be, so future contributors don't have to reverse-engineer intent from prose or re-litigate settled questions.

## When to Write an ADR

Write an ADR when a change:

- Alters a component boundary or the interface between two components (see [ARCHITECTURE.md §4](../../ARCHITECTURE.md#4-component-boundaries)).
- Changes platform scope (e.g., adding a new supported storage type or firmware mode).
- Chooses between two or more credible alternative approaches, where the choice has real cost to reverse later.
- Rejects a reasonable-sounding alternative — recording *why not* is often more valuable than recording *why*.

You do not need an ADR for routine documentation fixes, wording clarifications, or additive detail that doesn't change a decision already on record.

## Process

1. Copy [0001-record-architecture-decisions.md](0001-record-architecture-decisions.md) as a structural template (Context / Decision / Consequences).
2. Name the new file `NNNN-short-kebab-case-title.md`, incrementing `NNNN` from the highest existing ADR number.
3. Set status to `Proposed` and open it as a pull request for discussion, per [CONTRIBUTING.md](../../CONTRIBUTING.md#proposing-an-adr).
4. On merge, update the status to `Accepted`. If a later ADR reverses or replaces an earlier one, mark the old one `Superseded by ADR-NNNN` rather than deleting it — the history is the point.

## Status Values

| Status | Meaning |
|---|---|
| `Proposed` | Open for discussion, not yet decided. |
| `Accepted` | Decided and in effect. |
| `Superseded by ADR-NNNN` | No longer in effect; see the referenced ADR. |
| `Rejected` | Considered and explicitly not adopted, kept for reference. |

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-three-component-separation.md) | Three-component separation | Accepted |
| [0003](0003-clonezilla-as-deployment-engine.md) | Clonezilla as the deployment engine | Accepted |
| [0004](0004-bash-as-primary-implementation-language.md) | Bash as the primary implementation language | Accepted |
| [0005](0005-yaml-as-unified-configuration-format.md) | YAML as the unified configuration format | Accepted |
| [0006](0006-bcs-unified-cli-architecture.md) | `bcs` as a unified CLI, not three component CLIs | Accepted |
| [0007](0007-python-for-the-bcs-cli.md) | Python (Typer/Rich/Pydantic/PyYAML) for the `bcs` CLI, superseding Bash for this component | Accepted |

This index should be kept in sync with the files in this directory whenever an ADR is added or its status changes.
