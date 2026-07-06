# ADR-0006: `bcs` as a Unified CLI, Not Three Component CLIs

**Status:** Accepted

## Context

Boot Manager, Builder, and Deploy are deliberately separate components (`ADR-0002`), but a human operator still needs one thing to type. Left unresolved, the natural failure mode is three independent command-line tools (`builder-cli build`, `deploy-cli install`, `deploy-cli deploy`, and so on) each inventing its own flag conventions, exit codes, and configuration loading — which would multiply the "recipe/manifest" naming-ambiguity mistake `ADR-0005` closed, this time across the *interface* technicians use every day instead of a file format.

A second question, orthogonal to the first but decided together because it shapes the same executable: how does `bcs` grow new commands over the project's 10-year horizon without every extension requiring a change to `bcs`'s own source?

## Decision

**One executable, `bcs`, is the single entry point** for every component. It dispatches built-in commands (`doctor`, `validate`, `build`, `install`, `deploy`, `backup`, `restore`, `update`, `version`, `config`) to whichever component owns them (see [docs/CLI.md — Command Ownership](../CLI.md#command-ownership)) without becoming a fourth component itself — `bcs` contains no business logic of its own beyond dispatch, environment diagnostics, config validation, and self-management.

Three further decisions, made together as part of this same ADR because reversing any one late would mean reversing all of them:

1. **Git-style external plugin dispatch** (`bcs-<name>` on `PATH`) is the extensibility mechanism for anything beyond the built-in set, rather than an in-process plugin API.
2. **One shared exit code scheme** (0/1/2/3/4/5/6/7/8, plus 130/143 for signals) applies to every command — no command invents its own numbering.
3. **`install` and `deploy` are separate commands**, not one command with a fleet-size flag, because their failure models genuinely differ (`install` is atomic pass/fail; `deploy` can partially succeed across a classroom, which is why exit code `6` exists at all).

### Alternatives Considered

- **Three separate CLIs (`bm`, `builder`, `deploy`).** Rejected: reintroduces exactly the multi-format inconsistency `ADR-0005` closed for configuration, but for flags/exit codes/logging instead; also means an operator context-switches tools mid-task (build with one CLI, then deploy with another) for what is, from their side, one workflow.
- **An in-process plugin API** (a documented Bash function-registration protocol, or a compiled plugin ABI). Rejected: no case in this project needs anything beyond "run another command and pass arguments through" — the problem the git/kubectl `<tool>-<name>` convention already solves with zero additional machinery, consistent with Bash as the primary implementation language (`ADR-0004`) and this project's general preference for boring, proven mechanisms over building new ones (see the reasoning in `ADR-0003` for Clonezilla itself).
- **A single `install`/`deploy` command distinguished by a `--fleet`/`--classroom` flag.** Rejected — see [docs/CLI.md § Why `install` and `deploy` Are Separate](../CLI.md#why-install-and-deploy-are-separate). The two have different failure semantics (atomic vs. partial) that a shared exit-code scheme has to represent honestly; collapsing them into one command would mean deciding, awkwardly, whether `bcs install --fleet` can return "some machines failed" the same way `bcs deploy` does.
- **Per-command bespoke exit codes** (each command defining its own 0–255 meaning, as many single-purpose Unix tools do). Rejected: `bcs` is one tool with ten commands that a script may chain together; a shared scheme means a wrapper script's error handling doesn't need a per-command lookup table.

## Consequences

- Every built-in command shares one flag vocabulary, one config-loading precedence, one logging/verbosity system, and one exit code scheme — all defined once in [docs/CLI.md](../CLI.md) rather than per command.
- Third-party or centre-specific commands are added by dropping a `bcs-<name>` executable on `PATH`, with no `bcs` release required — but also with no sandboxing, which is an accepted, explicitly documented trust boundary (see [docs/CLI.md § Security Considerations](../CLI.md#security-considerations)), not an oversight.
- `bcs`'s own interface now has a SemVer discipline independent of the platform's: a new command or flag is a MINOR bump, per [docs/CLI.md § Extensibility & Versioning](../CLI.md#extensibility--versioning).
- Because `bcs` deliberately contains no business logic, this ADR does not change any of `ADR-0002`'s component boundaries — it formalizes the missing piece (how a human reaches those components) without touching what they are.
- The exit code `6` (partial failure) and the `install`/`deploy` split are now load-bearing design commitments; a future change that merges them back into one command would need its own superseding ADR, not a quiet refactor.
