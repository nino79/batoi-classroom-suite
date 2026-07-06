# Boot Manager — Specification

This expands [SPECIFICATION.md §2.1](../../SPECIFICATION.md#21-boot-manager) with acceptance-level detail. Requirement IDs (`BM-xxx`) remain owned by `SPECIFICATION.md`; this document adds the detail needed to design and later test against them. See [docs/architecture/boot-manager.md](../architecture/boot-manager.md) for the design rationale.

## Requirements Detail

### BM-001 — Bounded Boot Menu Presentation

- The menu MUST appear (or the configured default MUST be taken) within a bounded, configurable timeout.
- The timeout value is part of the deployment's configuration, not hard-coded, so different classrooms (or exam-mode machines) can tune it.
- **Acceptance:** with a given timeout `T` and no user input, the machine reaches its default boot target within `T` seconds of firmware handoff, on every supported hardware profile.

### BM-002 — Minimum Two Boot Paths

- **Normal boot:** straight into the installed LliureX 23 system, no menu interaction required beyond the default timeout.
- **Maintenance boot:** hands control to Deploy (see `BM-006`).
- Additional paths (e.g., a diagnostic/recovery shell) are permitted but not required for v1.0.

### BM-003 — UEFI NVRAM Boot Entry Management

- Boot Manager MUST ensure its own bootloader entry exists and is correctly ordered in UEFI NVRAM after deployment, without manual firmware-setup steps.
- MUST tolerate NVRAM entries being reset or reordered by firmware updates or user access to firmware setup, re-establishing itself on next opportunity where feasible.

### BM-004 — Themeable Branding

- Menu background, logo, icon set, and font MUST be loaded from configuration/asset files (see [assets/README.md](../../assets/README.md)), not embedded in Boot Manager logic.
- Replacing all four asset categories MUST NOT require a Boot Manager code change or rebuild.

### BM-005 — Safe Fallback

- If configuration is missing, unparseable, or references missing assets, Boot Manager MUST boot the installed OS directly.
- This fallback MUST NOT depend on the same configuration path that failed (i.e., the fallback logic itself must be simple enough not to share the failure mode).
- **Acceptance:** deliberately corrupting Boot Manager's configuration on a test machine still results in a normal boot into LliureX 23.

### BM-006 — Maintenance Request Interface

- Boot Manager MUST be able to identify the requesting machine (a stable machine identifier) when issuing a maintenance request to Deploy.
- The request MUST express, at minimum, "this machine wants to be (re-)imaged" or "this machine wants to join a scheduled deployment session."
- Exact transport/format is an open question tracked in [docs/architecture/boot-manager.md](../architecture/boot-manager.md#open-questions) and [docs/architecture/deploy.md](../architecture/deploy.md#open-questions), to be resolved jointly with Deploy.

### BM-007 — Localisation

- All user-facing menu text MUST be available in Valencian and Spanish at minimum.
- Language selection MAY be a configuration option or detected from a prior LliureX session setting; the mechanism is a Phase 1 design decision, not yet fixed.

## Non-Goals for This Component

- Boot Manager does not implement disk imaging itself (that's Deploy's responsibility, per `DEP-001`–`DEP-007`).
- Boot Manager does not manage curriculum/application-level configuration inside the LliureX session — its scope ends once normal boot hands off to the installed OS.
