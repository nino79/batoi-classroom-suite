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
