# scripts/

Maintainer and CI helper scripts (repository housekeeping — not BCS component implementation, which lives in [boot-manager/](../boot-manager/), [builder/](../builder/), and [deploy/](../deploy/)).

## Status

Empty placeholder. Per [AGENTS.md](../AGENTS.md) and the current [documentation-only phase](../ROADMAP.md), no scripts are implemented yet. This directory exists so the repository's intended shape is visible from the start, and so future automation (docs linting, ADR index checks, label sync) has an obvious home.

## Anticipated Contents

- Documentation consistency checks (e.g., verifying cross-references between `SPECIFICATION.md` and `docs/specifications/*.md` stay in sync).
- `.github/LABELS.md` → GitHub label sync tooling.
- Release/versioning helpers once components reach implementation.
