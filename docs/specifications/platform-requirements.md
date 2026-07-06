# Platform Requirements

This expands [SPECIFICATION.md §1](../../SPECIFICATION.md#1-target-platform-matrix) with the reasoning and detail behind each platform requirement. It is descriptive, not additionally normative — the requirement IDs and their exact wording remain owned by `SPECIFICATION.md`.

## PLAT-001 / PLAT-002 — LliureX 23 on Ubuntu 24.04 LTS

[LliureX](https://lliurex.net/) is the Valencian public education system's Linux distribution, maintained by the Conselleria d'Educació. LliureX 23 is the version in scope for BCS, built on Ubuntu 24.04 LTS. Pinning to a specific LliureX/Ubuntu pairing (rather than "whatever LliureX version is current") is deliberate: Builder's reproducibility guarantee (`BLD-005`) depends on a fixed base, and a moving target would undermine it. Moving to a future LliureX/Ubuntu pairing is expected to be a deliberate, versioned change to this requirement — not silent drift.

## PLAT-003 / PLAT-004 — UEFI Only, Secure Boot Aware

Classroom hardware refreshes at CIPFP Batoi (and comparable centres) have moved entirely to UEFI-only firmware; supporting legacy BIOS/CSM would double the boot-path testing surface for a code path with declining real-world relevance. UEFI is therefore the only supported firmware interface.

Secure Boot is a related but distinct concern: many UEFI machines ship with Secure Boot enabled by default, and Boot Manager's own boot chain must either work within that (via a signed chain of trust, see [ADR-0003](../decisions/0003-clonezilla-as-deployment-engine.md) for related tooling constraints) or the deployment must explicitly and visibly disable it as a documented step — never silently fail or silently disable it without operator awareness.

## PLAT-005 — NVMe as Primary Storage

NVMe (`/dev/nvme*`) is the primary supported storage target because it's what current and near-future classroom hardware ships with. SATA SSDs may happen to work through the same partclone-based imaging path, but they are not a target Deploy is validated or tested against, and regressions affecting only SATA are not release blockers for v1.0. Spinning disks are explicitly out of scope (see [SPECIFICATION.md §4](../../SPECIFICATION.md#4-explicit-non-goals)).

## PLAT-006 — Clonezilla as the Deployment Engine

Clonezilla (both Live and Server Edition, used as appropriate per component) is the deployment engine Deploy orchestrates. See [ADR-0003](../decisions/0003-clonezilla-as-deployment-engine.md) for the alternatives considered and the reasoning behind this choice.

## PLAT-007 — Wired Classroom LAN with PXE and Multicast

BCS assumes a managed, wired classroom LAN capable of PXE network boot and IP multicast — the network conditions that make `DEP-001`/`DEP-002`/`DEP-007` (whole-classroom multicast deployment within a class period) achievable. Wireless-only networks, or networks without multicast support (some managed switches disable it by default), are out of scope; centres deploying BCS are expected to have (or be willing to configure) this network baseline.

## Compatibility Matrix Summary

| Dimension | In Scope | Explicitly Out of Scope |
|---|---|---|
| OS | LliureX 23 / Ubuntu 24.04 LTS | Other LliureX/Ubuntu versions |
| Firmware | UEFI (Secure Boot aware) | Legacy BIOS/CSM |
| Storage | NVMe | SATA SSD (best-effort only), spinning disks |
| Deployment engine | Clonezilla | Custom cloning implementation |
| Network | Wired LAN, PXE + multicast capable | Wireless-only, non-multicast-capable networks |
