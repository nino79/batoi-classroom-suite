# Roadmap

This roadmap tracks the phased delivery of Batoi Classroom Suite (BCS). It is a living document: phases and dates will be refined as the architecture is validated against real classroom deployments at CIPFP Batoi.

Status legend: ✅ Done · 🚧 In progress · ⏳ Planned · 💤 Not started

## Phase 0 — Foundation: Architecture & Governance

**Goal:** agree on scope, boundaries, and requirements before writing implementation code.

| Item | Status |
|---|---|
| Project mission, README, and repository structure | 🚧 |
| System architecture (`ARCHITECTURE.md`) | 🚧 |
| Functional & non-functional specification (`SPECIFICATION.md`) | 🚧 |
| Contribution workflow, Code of Conduct, Security policy | 🚧 |
| Initial Architecture Decision Records | 🚧 |
| Issue/PR templates and label taxonomy | 🚧 |
| Unified configuration format (`docs/CONFIGURATION.md`, `config/schema.yaml`) | ✅ |
| `bcs` CLI design (`docs/CLI.md`) | ✅ |
| `bcs` CLI framework implementation (`cli/`, Python — [ADR-0007](docs/decisions/0007-python-for-the-bcs-cli.md)) | ✅ |
| Host Inventory subsystem design (`docs/HOST_INVENTORY.md`, [ADR-0008](docs/decisions/0008-host-inventory-ports-and-adapters.md) — Accepted) | ✅ |
| Platform Layer / Command Runner design (`docs/PLATFORM_LAYER.md`, [ADR-0009](docs/decisions/0009-platform-layer-command-runner.md) — Accepted) | ✅ |
| EFI Adapter design, first Host Discovery adapter (`docs/EFI_ADAPTER.md`, [ADR-0010](docs/decisions/0010-efi-adapter-read-only-scope.md) — Accepted) | ✅ |

This phase's primary output is the documentation set in this repository. The one exception is the `bcs` CLI framework itself (`--help`, `version`, `doctor`, `validate`, with `build`/`install`/`deploy`/`backup`/`restore`/`update`/`config` as unimplemented stubs) — a deliberate, scoped exception, not a sign Boot Manager/Builder/Deploy implementation has started; those remain gated on this phase's review before Phase 1 begins.

## Phase 1 — Boot Manager: Design Validation

**Goal:** validate the boot-time architecture against real UEFI/NVMe classroom hardware.

- ⏳ Boot menu configuration schema (recipe format for entries, theming, timeouts)
- ⏳ UEFI NVRAM boot-entry management strategy, validated on target hardware models
- ⏳ Fallback/safe-mode behaviour design (BM-005)
- ⏳ Maintenance-request interface design (BM-006) shared with Deploy
- ⏳ Secure Boot compatibility assessment

## Phase 2 — Builder: Golden Image Pipeline

**Goal:** define and validate a reproducible build pipeline for a LliureX 23 golden image.

- ✅ Recipe/configuration format (package sets, configuration, branding) — see [docs/CONFIGURATION.md](docs/CONFIGURATION.md) and [config/schema.yaml](config/schema.yaml); a validator implementation is still 💤
- ⏳ Build provenance and versioning scheme, aligned with `VERSION` and `CHANGELOG.md`
- ⏳ Output format validated against Clonezilla/partclone compatibility
- ⏳ First reproducible reference image built from a minimal recipe

## Phase 3 — Deploy: Single-Classroom Rollout

**Goal:** deploy a Builder-produced image to one real classroom.

- ⏳ PXE network boot integration
- ⏳ Unicast (single machine) deployment flow
- ⏳ Multicast (whole classroom) deployment flow via Clonezilla
- ⏳ Disk layout restoration (ESP + recovery partition) on NVMe targets
- ⏳ Per-machine, per-session deployment reporting (DEP-005)

## Phase 4 — Integration: Closed Loop

**Goal:** connect Boot Manager and Deploy so a machine can request its own re-imaging.

- ⏳ Boot Manager maintenance path triggers a Deploy session end-to-end
- ⏳ Scheduled/whole-classroom re-imaging triggered from any machine in the room
- ⏳ End-to-end integration test across all three components

## Phase 5 — Hardening & Scale

**Goal:** move from "works for one classroom" to "safe to run across the centre."

- 💤 UEFI Secure Boot signing pipeline for Builder output
- 💤 Multi-classroom / multi-centre deployment orchestration
- 💤 Deployment monitoring/reporting dashboard
- 💤 Security review against `SECURITY.md` threat model

## v1.0 — General Availability

**Goal:** a documented, supported release that CIPFP Batoi (and other interested centres) can run in production.

- 💤 Stable interfaces between all three components
- 💤 Full user- and operator-facing documentation in `docs/`
- 💤 Migration/upgrade path for existing classrooms

## Out of Scope (for now)

Items explicitly deferred beyond v1.0, tracked here so they aren't silently forgotten:

- Legacy BIOS / non-UEFI hardware support
- Spinning-disk / non-NVMe primary targets
- General-purpose fleet configuration management beyond classroom deployment

See [SPECIFICATION.md §4](SPECIFICATION.md#4-explicit-non-goals) for the full non-goals list.

---

Roadmap changes that affect scope or architecture should be accompanied by an [ADR](docs/decisions/) and a `CHANGELOG.md` entry once implementation begins.
