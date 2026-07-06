# Naming Conventions

A single reference for every naming rule used across BCS, so a rule is defined once and linked from wherever it's relevant, rather than restated (and inevitably drifting) in multiple places.

## Files and Directories

| Item | Convention | Example |
|---|---|---|
| Root governance files | `UPPERCASE.md` (GitHub convention) | `README.md`, `ARCHITECTURE.md`, `CODE_OF_CONDUCT.md` |
| Documentation files under `docs/` | `kebab-case.md` | `bash-style-guide.md`, `repository-organization.md` |
| ADRs | `NNNN-kebab-case-title.md`, zero-padded to 4 digits, sequential | `0003-clonezilla-as-deployment-engine.md` |
| Directories | `kebab-case` | `boot-manager/`, `docs/specifications/` |
| Bash scripts | `kebab-case.sh` | `build-golden-image.sh` |

## Domain-Driven Naming

**Rule:** Packages, adapters, and Pydantic models are named after the business/domain concept they represent, never after the implementation technology behind them.

This applies most concretely to `bcs.platform.adapters.*` (Platform Layer adapters wrapping external tools — see [docs/PLATFORM_LAYER.md](../PLATFORM_LAYER.md)) and to the models they produce:

| Instead of (implementation-technology name) | Use (domain name) | Why |
|---|---|---|
| `bcs.platform.adapters.efibootmgr` | `bcs.platform.adapters.efi` | The package represents the EFI domain, not the current backend tool. A future reimplementation (`efivarfs`, `libefivar`, or anything else) can replace `efibootmgr` internally without a public rename. |
| `EfiBootConfiguration` | `FirmwareBootConfiguration` | Names the firmware fact the model represents, not the tool that reported it — and avoids colliding with the *different*, already-existing concept of Boot Manager's own menu configuration (`spec.bootManager.menu`). |
| `EfibootmgrError` / `EfibootmgrParseError` | `FirmwareBootError` / `FirmwareBootParseError` | An error about firmware boot data, not about a specific CLI tool having failed. |

**Rationale:**

- **Adapters exist precisely so the rest of the codebase doesn't need to know which tool is behind them** ([docs/PLATFORM_LAYER.md § Purpose](../PLATFORM_LAYER.md#purpose)). A tool-named package undermines its own reason for existing — every caller's import statement would encode an implementation detail the adapter was supposed to hide.
- **Tool choices are more volatile than domain concepts.** `efibootmgr` could be replaced by a different mechanism for reading UEFI NVRAM variables; "the EFI domain" does not change when that happens. Naming things after what changes less keeps a rename out of the critical path when an implementation swap does happen.
- **Domain names carry meaning to a reader who has never heard of the specific tool.** `FirmwareBootConfiguration` is understandable to someone who has never run `efibootmgr`; `EfiBootConfiguration`-tied-to-`efibootmgr` requires that context.
- This does **not** mean the tool disappears from the documentation or code — describing *which* tool an adapter currently wraps, and that tool's specific version/flag/output quirks, remains necessary, factual, implementation detail (see, e.g., [docs/EFI_ADAPTER.md § Supported `efibootmgr` Versions](../EFI_ADAPTER.md#supported-efibootmgr-versions)). The rule is about the **public names** (packages, classes, functions other code imports), not about erasing the tool from prose or from the one module (`adapter.py`, by Platform Layer convention) that actually knows it.

First applied in [ADR-0010](../decisions/0010-efi-adapter-read-only-scope.md); see [docs/EFI_ADAPTER.md § Pydantic Models](../EFI_ADAPTER.md#pydantic-models) for a worked example of the naming decision, including a real naming collision it avoids.

## Requirement IDs

Fixed prefixes, defined in [SPECIFICATION.md](../../SPECIFICATION.md) — do not introduce a new prefix without updating that document:

| Prefix | Scope |
|---|---|
| `PLAT-NNN` | Platform/target environment requirements |
| `BM-NNN` | Boot Manager requirements |
| `BLD-NNN` | Builder requirements |
| `DEP-NNN` | Deploy requirements |
| `NFR-NNN` | Non-functional requirements |
| `CLI-NNN` | `bcs` command-line interface requirements |

`NNN` is a zero-padded 3-digit sequential number per prefix, never reused even if a requirement is later removed (removed IDs are marked as retired in `SPECIFICATION.md`, not recycled).

## Git Branches

Pattern: `type/short-description`, matching the Conventional Commits type it primarily contains (see [CONTRIBUTING.md](../../CONTRIBUTING.md#workflow)):

```
docs/boot-manager-fallback-clarify
adr/clonezilla-alternatives
feat/deploy-multicast-retry
fix/deploy-checksum-mismatch
```

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, imperative mood, lowercase summary, no trailing period.

```
docs(spec): clarify BLD-005 reproducibility scope
feat(deploy): add multicast session retry
adr: record decision on bash as primary language
```

Valid types: `feat`, `fix`, `docs`, `chore`, `adr`, `refactor`, `test`. Scope is typically a component (`boot-manager`, `builder`, `deploy`) or a root doc area (`spec`, `arch`).

## GitHub Labels

`category: value`, lowercase, defined exhaustively in [.github/LABELS.md](../../.github/LABELS.md). Don't invent a label outside that document without updating it first.

## Version Tags

[Semantic Versioning](https://semver.org/): `vX.Y.Z`, matching the single-line value in [VERSION](../../VERSION) at release time. Pre-1.0 (`v0.y.z`) means any part of the public interface may still change — see [docs/processes/release-process.md](../processes/release-process.md).

## Bash

See [bash-style-guide.md](bash-style-guide.md) for full context; naming rules specifically:

| Item | Convention | Example |
|---|---|---|
| Functions, local variables | `lower_snake_case` | `validate_recipe`, `image_path` |
| Constants, environment/exported variables | `UPPER_SNAKE_CASE` | `readonly MAX_RETRIES=3` |
| Private/internal functions | `_leading_underscore` | `_parse_config_header` |

## Configuration Keys

**This section supersedes earlier guidance.** BCS's YAML configuration (`config/schema.yaml`, formalized in [docs/CONFIGURATION.md](../CONFIGURATION.md) and [ADR-0005](../decisions/0005-yaml-as-unified-configuration-format.md)) uses `camelCase` keys throughout (`bootManager`, `menuTimeoutSeconds`, `pinnedSnapshot`), matching Kubernetes and Docker Compose convention rather than Bash's `snake_case`. An earlier version of this document assumed recipe keys would be sourced directly into Bash as environment variables and should therefore be `snake_case` — that assumption predated the configuration format actually being designed and is now incorrect. Any Bash code that reads configuration values is expected to go through an explicit access layer (e.g., a `yq`/`jq`-style query, or a small parsing function), not by sourcing the YAML file directly as shell variables, so there is no longer a reason to constrain YAML key casing to Bash's naming rules.

## Machine Identifiers

The stable machine identifier Boot Manager uses in maintenance requests (`BM-006`) does not yet have a defined format — this is an open, jointly-owned question between Boot Manager and Deploy (see [docs/architecture/boot-manager.md](../architecture/boot-manager.md#open-questions)). Once decided, its format will be recorded here.
