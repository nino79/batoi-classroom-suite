# Builder

Produces the versioned, reproducible LliureX 23 golden image consumed by [Deploy](../deploy/).

## Status

📋 **Specification phase** — no implementation yet. See [ROADMAP.md](../ROADMAP.md#phase-2--builder-golden-image-pipeline) (Phase 2) for what's planned next.

## Documentation

- Design and rationale: [docs/architecture/builder.md](../docs/architecture/builder.md)
- Requirements: [docs/specifications/builder.md](../docs/specifications/builder.md)
- Recipe/configuration format: [docs/CONFIGURATION.md](../docs/CONFIGURATION.md) and [config/schema.yaml](../config/schema.yaml)
- CLI entry point: [`bcs build`](../docs/CLI.md#bcs-build)
- Requirement IDs referenced below (`BLD-xxx`) are defined in [SPECIFICATION.md §2.2](../SPECIFICATION.md#22-builder).

## Scope

- Accept a declarative recipe — the `spec.builder`/`spec.packages` sections of the unified [BCS configuration](../docs/CONFIGURATION.md) — describing package sets, configuration, and branding (`BLD-001`).
- Produce a versioned, traceable image artifact (`BLD-002`).
- Produce Clonezilla/partclone-compatible output (`BLD-003`).
- Lay out a UEFI-compatible (GPT + ESP) partition scheme for NVMe targets (`BLD-004`).
- Produce reproducible builds from the same recipe and pinned inputs (`BLD-005`).
- Record build provenance: recipe version, base OS version, build date, checksum (`BLD-006`).

## Out of Scope

Distributing images to machines (owned by [Deploy](../deploy/)) and boot-time behaviour (owned by [Boot Manager](../boot-manager/)) — see [ARCHITECTURE.md](../ARCHITECTURE.md) for the full component boundary rationale.

## Planned Layout

This is the anticipated structure once implementation begins (Phase 2); nothing below exists yet beyond this README:

```
builder/
├── README.md          # this file
├── docs/              # component-local notes (cross-linked from docs/architecture, docs/specifications)
├── recipes/           # per-classroom ClassroomConfig YAML files (see docs/CONFIGURATION.md)
└── src/               # implementation (not started)
```
