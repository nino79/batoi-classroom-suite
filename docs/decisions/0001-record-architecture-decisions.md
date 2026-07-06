# ADR-0001: Record Architecture Decisions

**Status:** Accepted

## Context

Batoi Classroom Suite (BCS) is being built as three long-lived components (Boot Manager, Builder, Deploy) that will be maintained across school years and hardware refreshes, likely by contributors who were not present when a given decision was made. Prose documents like `ARCHITECTURE.md` and `SPECIFICATION.md` are good at describing the *current* state, but they naturally get edited in place over time, which erases the reasoning, alternatives, and trade-offs that led to that state.

Without a durable record of *why*, future contributors (human or AI agent) tend to either re-litigate settled questions or, worse, silently reverse a decision without realizing it was deliberate.

## Decision

We will record architecturally significant decisions as Architecture Decision Records (ADRs) in `docs/decisions/`, using a lightweight Context/Decision/Consequences format (based on Michael Nygard's original ADR proposal). Each ADR is numbered sequentially and immutable once accepted — later changes get a new ADR that supersedes it, rather than an edit to the original.

The full process, including when an ADR is warranted, is documented in [docs/decisions/README.md](README.md).

## Consequences

- Contributors get a chronological, append-only record of *why* the architecture looks the way it does, separate from the always-current description in `ARCHITECTURE.md`/`SPECIFICATION.md`.
- Proposing a significant change requires slightly more ceremony than editing prose directly — this is intentional friction for decisions that are expensive to reverse.
- ADRs must be kept discoverable: the index in [docs/decisions/README.md](README.md) needs to stay in sync, or this record degrades into the same problem it's meant to solve.
