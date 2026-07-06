# Coding Standards

These are the cross-cutting principles that apply to any implementation code in BCS, regardless of language. Bash-specific syntax rules are in [bash-style-guide.md](bash-style-guide.md); this document covers the *why* and the *what*, not language mechanics.

Boot Manager, Builder, and Deploy have no implementation code yet (see [ROADMAP.md](../../ROADMAP.md)) — most of this document was written ahead of their implementation deliberately, so that the first lines of code are held to the same bar as line 100,000. The `bcs` CLI (`cli/`) is implemented and is where the Python-specific rules below (see [§ OS Interaction](#os-interaction-python-components)) already apply in practice.

## Language Policy

Bash is the primary implementation language for all three components, per [ADR-0004](../decisions/0004-bash-as-primary-implementation-language.md). Deviating from Bash for a component's core logic is an exception that needs its own justification, not a default choice — see the ADR for the reasoning and the narrow carve-out for Builder tooling.

## Error Handling

- **Fail loudly during build/deploy, fail safely at boot.** Builder and Deploy operations should stop and report clearly on unexpected error conditions (per `NFR-004`, auditability) rather than continuing silently. Boot Manager is the one exception: per `BM-005`, it must degrade to a safe fallback rather than halting, because it runs unattended on every boot.
- **Every failure is attributable.** An error must be traceable to a specific machine, session, or build (per `NFR-004`) — a bare "something went wrong" is not acceptable in a tool a single technician uses to audit a 30-machine classroom rollout.
- **Don't swallow errors to make output quieter.** If an error is genuinely not actionable, say so explicitly (and why) rather than suppressing it.

## Idempotency

Per `NFR-007`, re-running an operation against a target already at the desired state must be safe and must not be required for normal operation. Concretely:

- Deploy operations must detect "already at target image version" and treat re-running as a no-op success, not an error, and not a redundant re-image.
- Builder operations given the same recipe and pinned inputs should be safely re-runnable without manual cleanup between runs (supports `BLD-005`, reproducibility).
- Boot Manager configuration changes should be safe to apply repeatedly (e.g., re-registering a UEFI boot entry that already exists, per `BM-003`, must not create duplicates).

## Domain-Driven Naming

**Packages, adapters, and Pydantic models are named after the business/domain concept they represent, never after the implementation technology behind them** — e.g. `bcs.platform.adapters.efi` and `FirmwareBootConfiguration`, not `.efibootmgr`/`EfiBootConfiguration`. This keeps a swappable implementation choice (which specific tool an adapter currently shells out to) from leaking into public names that the rest of the codebase, and future contributors unfamiliar with that specific tool, depend on. Full rule, rationale, and a worked example: [docs/standards/naming-conventions.md § Domain-Driven Naming](naming-conventions.md#domain-driven-naming). First applied in [ADR-0010](../decisions/0010-efi-adapter-read-only-scope.md).

## OS Interaction (Python Components)

**Direct use of `subprocess.run()`, `subprocess.Popen()`, or equivalent (`os.system`, `os.popen`, `os.exec*`) outside `bcs.platform` is forbidden.** This is a hard prohibition, not a style preference: every external process `cli/`'s code spawns MUST go through the Platform Layer's `CommandRunner` (`NFR-008`) — the one seam where OS interaction is centralized, logged, and timeout-bounded. See [docs/PLATFORM_LAYER.md](../PLATFORM_LAYER.md) and [ADR-0009](../decisions/0009-platform-layer-command-runner.md).

- **Commands are always an argument list, never a shell string.** `shell=True` is never passed to `subprocess`, anywhere, under any circumstance — see [docs/PLATFORM_LAYER.md § Architectural Rule: Argument Lists Only](../PLATFORM_LAYER.md#architectural-rule-argument-lists-only-never-shelltrue). This is enforced mechanically, not just by review: `cli/pyproject.toml` scopes Ruff's Bandit-derived `S603`/`S607` subprocess-call warnings to fail on any file outside the two reviewed exceptions (`bcs.plugins`, `bcs.platform.execution`).
- The one reviewed exception is `bcs.plugins.run_plugin`'s plugin dispatch, which needs full passthrough stdio for interactive plugins — see [docs/PLATFORM_LAYER.md § Relationship to Existing Code](../PLATFORM_LAYER.md#relationship-to-existing-code) for why this is a deliberate, narrow carve-out and not a precedent for anything else.

## Logging and Observability

- Logs are a primary interface for the single technician operating BCS (see the "single technician is the operator" design principle in [docs/architecture/overview.md](../architecture/overview.md#design-principles)) — write for that reader, not for a hypothetical log-aggregation pipeline.
- Every log line that represents a decision (e.g., "falling back to normal boot because configuration was invalid") should state *why*, not just *what*.
- Deploy's session reports (`DEP-005`) are a structured artifact, not just captured log output — design them to be read without scrolling through raw logs.

## Testing Expectations

- Each component must remain independently testable (`NFR-005`) — a test for Deploy must not require Boot Manager or Builder to be present, only the documented interface artifacts (see [ARCHITECTURE.md §4](../../ARCHITECTURE.md#4-component-boundaries)).
- Bash implementation code is expected to be covered by [bats](https://github.com/bats-core/bats-core) tests and pass [ShellCheck](https://www.shellcheck.net/) with no unjustified suppressions — see [bash-style-guide.md](bash-style-guide.md#tooling).
- Cross-component behavior is validated by the integration tests described in [tests/README.md](../../tests/README.md).

## Secrets and Configuration

- No implementation may embed long-lived shared credentials in a golden image (`NFR-003`) — configuration that varies by deployment (network settings, per-centre branding) is injected at build or deploy time, never hard-coded into component logic.
- Configuration is data, not code — see the "theming as data, not code" principle in [docs/architecture/boot-manager.md](../architecture/boot-manager.md#theming-as-data-not-code), which generalizes to recipes (Builder) and session definitions (Deploy) as well.

## Review Bar

Code review checks the same things documentation review does (see [docs/processes/development-workflow.md](../processes/development-workflow.md)): does this change trace back to a requirement ID, does it respect component boundaries, and — for anything touching an interface — is there an ADR.
