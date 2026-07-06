# ADR-0004: Bash as the Primary Implementation Language

**Status:** Accepted

## Context

Once Boot Manager, Builder, and Deploy move from specification into implementation (see [ROADMAP.md](../../ROADMAP.md)), a primary implementation language needs to be settled — not per-component ad hoc, since inconsistency here is exactly the kind of thing a 10-year-maintained project accumulates as regret.

The constraints differ somewhat by component, but share a common thread:

- **Boot Manager** and **Deploy**'s maintenance path run inside constrained environments: a boot-time context and a Clonezilla Live environment, respectively. Neither is guaranteed to have a full Python (or other interpreter) runtime available, but both are guaranteed a POSIX-ish shell, because that's what the underlying tooling (GRUB scripting, Clonezilla's own extensively Bash-based ocs-* scripts, initramfs hooks) already runs on.
- **Builder** runs on a build host with far fewer constraints — a full Ubuntu 24.04 environment with any interpreter available.
- The classroom-IT ecosystem BCS integrates with (Clonezilla, LliureX deployment tooling used historically at CIPFP Batoi and comparable centres) is itself overwhelmingly Bash-based. Technicians who maintain BCS after the original authors move on are more likely to be comfortable reading and patching Bash in this specific context than a Python codebase layered on top of fundamentally shell-driven tools.

### Alternatives Considered

- **Python throughout.** Rejected as the *primary* language: better for complex data structures and testing ergonomics, but adds a runtime dependency that isn't guaranteed in Boot Manager's boot-time context or in a minimal Clonezilla Live environment, and would put BCS's implementation language at odds with the ecosystem it's integrating with.
- **A different language per component with no stated default.** Rejected: this is precisely the inconsistency this ADR exists to prevent. Ten years of maintenance is long enough that "whatever the original author preferred" compounds into a real onboarding cost.
- **POSIX `sh` instead of Bash specifically.** Rejected: the target platform (`PLAT-001`–`PLAT-007`) guarantees Bash (it's Ubuntu/LliureX's default shell and Clonezilla's own scripting language), so restricting to POSIX `sh` would forfeit Bash-specific features (arrays, `[[ ]]`, `local`) for a portability guarantee BCS doesn't need.

## Decision

**Bash is the primary implementation language for all three BCS components.** Scripts must follow the conventions in [docs/standards/bash-style-guide.md](../standards/bash-style-guide.md).

Builder — which runs on an unconstrained build host — may use a higher-level language (e.g., Python) for genuinely complex logic where Bash would be a poor fit (structured recipe/manifest validation, for instance), but any such use is a deliberate exception, documented at the point it's introduced, not a default. Boot Manager and Deploy's maintenance-path logic should be assumed Bash-only unless a future ADR revisits this.

## Consequences

- A single style guide ([docs/standards/bash-style-guide.md](../standards/bash-style-guide.md)) and a single set of tooling expectations (ShellCheck, `bats` for tests) cover essentially the whole codebase once implementation begins.
- Contributors need to be comfortable with Bash to work on Boot Manager or Deploy; this is treated as an acceptable, deliberate bar given the target ecosystem, not an accident.
- Any future proposal to introduce a second primary language for a component's core logic (not an isolated build-host tool) should be raised as a superseding ADR, referencing the constraints recorded here.
