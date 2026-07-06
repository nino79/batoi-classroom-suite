# Builder — Specification

This expands [SPECIFICATION.md §2.2](../../SPECIFICATION.md#22-builder) with acceptance-level detail. Requirement IDs (`BLD-xxx`) remain owned by `SPECIFICATION.md`; this document adds the detail needed to design and later test against them. See [docs/architecture/builder.md](../architecture/builder.md) for the design rationale.

## Requirements Detail

### BLD-001 — Declarative Recipe Input

- The recipe MUST describe, at minimum: package sets (base + per-subject/per-centre additions), configuration (network, locale, user profile defaults), and branding references (pointing into [assets/](../../assets/)).
- The recipe format itself (schema, file format) is a Phase 2 deliverable — see [ROADMAP.md](../../ROADMAP.md#phase-2--builder-golden-image-pipeline).

### BLD-002 — Versioned, Traceable Artifact

- Every produced image MUST carry a version identifier that can be traced back to the exact recipe version and base OS version (`PLAT-001`/`PLAT-002`) used.
- Version identifiers should be consistent with the project's own [VERSION](../../VERSION)/[CHANGELOG.md](../../CHANGELOG.md) scheme once Builder reaches implementation.

### BLD-003 — Clonezilla-Compatible Output

- Output MUST be consumable by Deploy via Clonezilla — i.e., partclone-compatible partition images (or the container format Clonezilla expects for a full-disk image set).
- See [ADR-0003](../decisions/0003-clonezilla-as-deployment-engine.md) for why Clonezilla is the fixed downstream consumer, which is what constrains this requirement.

### BLD-004 — UEFI-Compatible Partition Layout

- Output MUST include a GPT partition table and a correctly formatted EFI System Partition (ESP), plus the root filesystem, laid out for NVMe targets (`PLAT-005`).
- The layout MUST be discoverable by Boot Manager after Deploy restores it (see `DEP-003`).

### BLD-005 — Reproducibility

- Given the same recipe version and the same pinned base OS/package versions, two independent builds SHOULD produce the same package set and configuration (allowing for inherently non-deterministic elements like timestamps or generated machine IDs).
- "Reproducible" here means *auditable and explainable*, not necessarily bit-for-bit identical — the practical bar is a Phase 2 design decision (see [docs/architecture/builder.md](../architecture/builder.md#open-questions)).

### BLD-006 — Build Provenance

- Every artifact MUST record: recipe version, base OS version, build timestamp, and a checksum of the resulting image.
- This provenance record is what Deploy verifies against at deployment time (`DEP-004`) and what an incident investigation traces back to (`NFR-004`).

## Non-Goals for This Component

- Builder does not distribute images to machines (that's Deploy).
- Builder does not decide *when* a classroom gets re-imaged (that's a Deploy/operator decision, informed by a new Builder artifact being available).
- Builder is not a general-purpose OS image builder for non-LliureX targets.
