# Deploy

Distributes golden images from [Builder](../builder/) onto classroom fleets via Clonezilla, and verifies the result.

## Status

📋 **Specification phase** — no implementation yet. See [ROADMAP.md](../ROADMAP.md#phase-3--deploy-single-classroom-rollout) (Phase 3) for what's planned next.

## Documentation

- Design and rationale: [docs/architecture/deploy.md](../docs/architecture/deploy.md)
- Requirements: [docs/specifications/deploy.md](../docs/specifications/deploy.md)
- Requirement IDs referenced below (`DEP-xxx`) are defined in [SPECIFICATION.md §2.3](../SPECIFICATION.md#23-deploy).

## Scope

- Image a single machine (unicast) or a whole classroom (multicast) from the same artifact (`DEP-001`).
- Support PXE network boot as the deployment entry point (`DEP-002`).
- Restore the disk layout Boot Manager expects on NVMe targets (`DEP-003`).
- Verify deployed images against Builder's checksum (`DEP-004`).
- Produce per-session, per-machine deployment reports (`DEP-005`).
- Accept maintenance/re-imaging requests from [Boot Manager](../boot-manager/) (`DEP-006`).
- Complete a full-classroom deployment within a class period (`DEP-007`).

## Out of Scope

Building images (owned by [Builder](../builder/)) and boot-time behaviour after imaging completes (owned by [Boot Manager](../boot-manager/)) — see [ARCHITECTURE.md](../ARCHITECTURE.md) for the full component boundary rationale.

## Planned Layout

This is the anticipated structure once implementation begins (Phase 3); nothing below exists yet beyond this README:

```
deploy/
├── README.md          # this file
├── docs/              # component-local notes (cross-linked from docs/architecture, docs/specifications)
├── sessions/          # deployment session definitions/reports
└── src/               # implementation (not started)
```
