# Changelog

All notable changes to Batoi Classroom Suite (BCS) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). BCS is still overwhelmingly documentation-first — Boot Manager, Builder, and Deploy remain unimplemented — so version numbers largely track the maturity of the *specification*; the `bcs` CLI framework is the first exception with real, tested code.

## [Unreleased]

### Added

- Full documentation set: `ARCHITECTURE.md`, `SPECIFICATION.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `AGENTS.md`, `CLAUDE.md`.
- `docs/` tree: architecture deep-dives, component specifications, Architecture Decision Records, coding/Bash/Markdown/naming standards, development and release process docs, contributor guides, and glossary.
- `.github/` issue templates, pull request template, label taxonomy, and Discussions category documentation.
- Placeholder READMEs describing the intended purpose of `boot-manager/`, `builder/`, `deploy/`, `scripts/`, `tools/`, `tests/`, and `assets/`.
- `REVIEW.md`: an independent, critical architecture review of the documentation set, with a prioritized punch list.
- Unified BCS configuration system: `config/schema.yaml` (normative JSON Schema, Kubernetes-style `apiVersion`/`kind`/`metadata`/`spec` envelope), `config/examples/default.yaml` (reference instance), and `docs/CONFIGURATION.md` (full field reference). Resolves the "recipe/manifest" naming ambiguity and the previously-undefined Builder recipe format (`BLD-001`) — see [ADR-0005](docs/decisions/0005-yaml-as-unified-configuration-format.md).

- `docs/CLI.md`: complete design of `bcs`, the unified command-line interface — command tree, global options, exit codes, logging/verbosity, color output, progress reporting, configuration loading, validation flow, and the git-style plugin system. New `CLI-001`–`CLI-014` requirements in `SPECIFICATION.md §2.4`. See [ADR-0006](docs/decisions/0006-bcs-unified-cli-architecture.md).
- `cli/`: the `bcs` CLI framework, implemented in Python (Typer, Rich, Pydantic, PyYAML) per [ADR-0007](docs/decisions/0007-python-for-the-bcs-cli.md) — global options, structured logging, `NO_COLOR`-aware output, the ClassroomConfig loader/override/validation pipeline (Pydantic models mirroring `config/schema.yaml`), git-style plugin dispatch, and the `version`/`doctor`/`validate` commands with placeholder check logic. `build`/`install`/`deploy`/`backup`/`restore`/`update`/`config` are registered as stubs.
- `.pre-commit-config.yaml` and `.github/workflows/ci.yml`: lint (Ruff), type-check (mypy), and test (pytest, Python 3.12/3.13) gates for `cli/`, plus a `bcs` smoke-test job.
- **Host Inventory subsystem** (`bcs.inventory`): immutable, extensible Pydantic models (`HostInventory` and its sections — firmware/Secure Boot, storage, network, identity, OS, CPU, memory, tooling), stdlib-only host collectors, and the `bcs inventory` command. This is BCS's single source of truth describing the current machine, consumed identically by `bcs doctor` (refactored to evaluate pass/fail against these same facts instead of probing the host a second time), and — once implemented — by Boot Manager, Builder, and Deploy, plus a future REST API/Web UI. Carries its own `bcs-inventory/v1alpha1` schema version, independent of `bcs-cli/v1alpha1` and `bcs/v1alpha1`. New `CLI-015` requirement in `SPECIFICATION.md §2.4`. `HostIdentity` narrows (does not resolve) the open `deploy.maintenanceRequests.machineIdentity` question. 209 pytest cases; Ruff, mypy (strict), pre-commit, and GitHub Actions CI all pass.
- `bcs.model_utils`: the `x-`-prefixed-extra-key validator shared by `bcs.config.models` and `bcs.inventory.models`, extracted so both domains can't drift on what counts as a valid extension key.
- `docs/HOST_INVENTORY.md`: a complete design proposal for the Host Inventory subsystem — package structure, Pydantic model diagram, per-class/module responsibilities, dependency graph, sequence diagrams, interaction with the CLI/future REST API/future Web UI, serialization strategy, testing strategy, a current-implementation-status-vs-proposal reconciliation table, and a numbered list of proposed changes requiring approval (a `caveats` field, a checked-in JSON Schema artifact, a golden-file schema-regression test). Supported by [ADR-0008](docs/decisions/0008-host-inventory-ports-and-adapters.md), formalizing the subsystem's ports-and-adapters split, immutability, and JSON-as-canonical-format decisions. **This is documentation only — no `.py`, `pyproject.toml`, or test files were changed**.
- [ADR-0008](docs/decisions/0008-host-inventory-ports-and-adapters.md) accepted: the ports-and-adapters split, immutability, and JSON-as-canonical-format decisions for the Host Inventory subsystem are now in effect. Approving the architecture does not, by itself, approve the individual items in `docs/HOST_INVENTORY.md`'s Proposed Changes Requiring Approval list (the `caveats` field, the checked-in JSON Schema artifact, the golden-file regression test) — those remain open. **Documentation only — no code changed.**

### Changed

- `docs/standards/naming-conventions.md`: configuration keys are `camelCase` (Kubernetes/Compose convention), superseding earlier `snake_case` guidance that predated the configuration format being designed; registered the new `CLI-NNN` requirement ID prefix.
- `docs/glossary.md`: "Recipe" now points to the concrete `ClassroomConfig` format instead of describing an undefined artifact; "manifest" is retired as a synonym.
- `ARCHITECTURE.md`: added `§8 Operator Interface`, describing `bcs` as the single entry point into all three components.
- `docs/CLI.md`: `Implementation Notes` now describes the actual Python layout under `cli/`, superseding the originally-planned Bash layout.
- `AGENTS.md`, `docs/repository-organization.md`: updated to reflect `cli/` as an implemented, tested exception to the documentation-only phase.

## [0.1.0] - 2026-07-06

### Added

- Initial project structure: `boot-manager/`, `builder/`, `deploy/`, `assets/`, `docs/`, `scripts/`, `tests/`, `tools/`.
- MIT `LICENSE`.
- Initial `README.md` describing the project's three components.

[Unreleased]: https://github.com/nino79/batoi-classroom-suite/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nino79/batoi-classroom-suite/releases/tag/v0.1.0
