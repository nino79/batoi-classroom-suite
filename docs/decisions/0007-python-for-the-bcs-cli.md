# ADR-0007: Python (Typer/Rich/Pydantic/PyYAML) for the `bcs` CLI, Superseding Bash for This Component

**Status:** Accepted

## Context

[ADR-0004](0004-bash-as-primary-implementation-language.md) made Bash the primary implementation language for BCS, reasoning from Boot Manager and Deploy's constrained boot-time/Clonezilla-Live execution environments, and from consistency with the Bash-heavy Clonezilla ecosystem. [ADR-0006](0006-bcs-unified-cli-architecture.md) then extended that choice specifically to `bcs`, describing it as "implemented as a Bash entry-point script... dispatching to per-command Bash scripts."

Implementation of the `bcs` CLI framework has now begun, with an explicit, specific brief: Python 3.12, Typer, Rich, Pydantic, and PyYAML. This is a direct reversal of ADR-0006's language choice for this one component, so it is recorded here rather than silently overriding prior ADRs — per this project's own rule that a choice with real cost to reverse gets an ADR (`docs/decisions/README.md`).

### Why This Doesn't Undermine ADR-0004

ADR-0004's reasoning was about **Boot Manager and Deploy's execution context**: a boot-time environment or a Clonezilla Live image, where a Python runtime is not guaranteed to be present. `bcs` itself does not run in either of those contexts — it runs on a technician's own workstation or a build host, which is exactly the kind of unconstrained environment ADR-0004 already carved out an exception for ("Builder... may use a higher-level language... for genuinely complex logic where Bash would be a poor fit"). `bcs` orchestrating Builder and Deploy from a normal desktop/CI environment is a closer fit to that carve-out than to the boot-time constraint the Bash mandate exists to satisfy. ADR-0004 itself is not revisited or weakened by this decision — it continues to govern Boot Manager and Deploy's own implementation, once those begin.

### What Changes as a Result

- ADR-0006 remains correct on architecture (one unified CLI, git-style plugin dispatch, the shared exit code scheme, the `install`/`deploy` split) — none of that depended on the implementation language. Only its "Implementation Notes" section's Bash-specific file layout is superseded; see the equivalent Python layout in [docs/CLI.md#implementation-notes](../CLI.md#implementation-notes) and [cli/README.md](../../cli/README.md).
- [docs/standards/bash-style-guide.md](../standards/bash-style-guide.md) no longer governs `bcs`'s own code. It still applies in full to Boot Manager and Deploy once their implementation begins, per ADR-0004.

### Why Typer + Rich + Pydantic + PyYAML Specifically

- **Typer** gives command/subcommand registration, type-hint-driven option parsing, and (via `typer.core.TyperGroup`) a documented seam for the git-style external plugin dispatch `ADR-0006` specifies — without needing a hand-rolled argument parser.
- **Rich** provides the TTY-aware, `NO_COLOR`-respecting console output `docs/CLI.md#color-output` and `#progress-reporting` require, including safe non-interactive fallback behavior, without reimplementing terminal detection.
- **Pydantic** (v2) gives `bcs` a typed, validating model of `config/schema.yaml` (see `bcs.config.models`) — closer to the schema's own intent (structural validation, defaults, `const`/`enum` constraints) than hand-written dictionary traversal would be, and is the natural implementation counterpart to a project that already committed to a formal JSON Schema for its configuration (`ADR-0005`).
- **PyYAML** is the direct, uncontested choice for reading/writing the YAML documents `ADR-0005` already established as the configuration format.

No dependency beyond these four was introduced for the CLI framework itself; see the ULID generator (`bcs.ulid`) implemented against the stdlib alone specifically to avoid adding a fifth.

## Decision

The `bcs` CLI is implemented in Python 3.12 using Typer, Rich, Pydantic, and PyYAML, per [cli/pyproject.toml](../../cli/pyproject.toml). This supersedes ADR-0006's Bash-based implementation notes for `bcs` specifically; it does not alter ADR-0004's language choice for Boot Manager, Builder, or Deploy.

## Consequences

- `bcs` now has its own quality-gate stack independent of the rest of the (currently Bash-oriented) implementation plan: Ruff (lint + format), mypy (strict), pytest, pre-commit, and GitHub Actions CI — see [cli/pyproject.toml](../../cli/pyproject.toml), [.pre-commit-config.yaml](../../.pre-commit-config.yaml), and [.github/workflows/ci.yml](../../.github/workflows/ci.yml).
- Contributors to `bcs` need Python 3.12 and familiarity with Typer/Pydantic idioms rather than the Bash conventions the rest of the platform is expected to use — a real, accepted cost given `bcs`'s role as the one component every operator interacts with directly.
- The Pydantic models in `bcs.config.models` are a second, executable expression of `config/schema.yaml`'s constraints (alongside the JSON Schema file itself). The two must be kept in sync by hand; this mirrors the existing discipline of keeping `docs/CLI.md`'s field tables in sync with `config/schema.yaml`; per `docs/standards/coding-standards.md`, and is an accepted duplication rather than deriving one from the other automatically, which is not designed yet.
- If Boot Manager or Deploy's own CLIs (if any are ever needed beyond what `bcs` dispatches to) are considered, this ADR does not imply they should also be Python — that would need its own ADR, weighed against ADR-0004's boot-time/Clonezilla-Live constraints, which do not apply to `bcs`.
