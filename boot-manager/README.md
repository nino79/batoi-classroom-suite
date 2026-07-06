# Boot Manager

Owns the boot-time experience on every LliureX classroom PC: the UEFI boot menu, boot-entry management, and the maintenance path back into [Deploy](../deploy/).

## Status

📋 **Specification phase** — no implementation yet. See [ROADMAP.md](../ROADMAP.md#phase-1--boot-manager-design-validation) (Phase 1) for what's planned next.

## Documentation

- Design and rationale: [docs/architecture/boot-manager.md](../docs/architecture/boot-manager.md)
- Requirements: [docs/specifications/boot-manager.md](../docs/specifications/boot-manager.md)
- Requirement IDs referenced below (`BM-xxx`) are defined in [SPECIFICATION.md §2.1](../SPECIFICATION.md#21-boot-manager).

## Scope

- Present a themed boot menu within a bounded timeout, or boot a configured default (`BM-001`).
- Offer a normal boot path and a maintenance boot path (`BM-002`).
- Manage UEFI NVRAM boot entries (`BM-003`).
- Apply branding from [`assets/`](../assets/) without code changes (`BM-004`).
- Fail safe to the installed OS if configuration is broken (`BM-005`).
- Issue maintenance/re-imaging requests to Deploy (`BM-006`).
- Support Valencian and Spanish UI text (`BM-007`).

## Out of Scope

Disk imaging itself (owned by [Deploy](../deploy/)) and building the OS image (owned by [Builder](../builder/)) — see [ARCHITECTURE.md](../ARCHITECTURE.md) for the full component boundary rationale.

## Planned Layout

This is the anticipated structure once implementation begins (Phase 1); nothing below exists yet beyond this README:

```
boot-manager/
├── README.md          # this file
├── docs/              # component-local notes (cross-linked from docs/architecture, docs/specifications)
├── config/            # boot menu schema, theming configuration
└── src/               # implementation (not started)
```
