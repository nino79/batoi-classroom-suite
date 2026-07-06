# ADR-0003: Clonezilla as the Deployment Engine

**Status:** Accepted

## Context

Deploy needs an underlying disk-cloning/imaging engine capable of restoring a golden image onto NVMe-based UEFI machines, at classroom scale, over a wired LAN, within a class period (`DEP-007`). This engine choice constrains Builder's output format (`BLD-003`) and Deploy's own orchestration design, so it needed to be settled early rather than discovered mid-implementation.

### Options Considered

- **Clonezilla** (Live and Server Edition) — a mature, widely deployed open-source disk cloning/imaging solution built on `partclone`, already familiar to school IT technicians in the LliureX/Spanish education ecosystem, with existing support for multicast, PXE-based network deployment, and GPT/UEFI-ESP-aware imaging.
- **FOG Project** — another open-source imaging solution with a web management UI and PXE integration, but with a smaller footprint in the specific school-IT ecosystem BCS targets, and less direct alignment with the partclone-based image format already familiar from Clonezilla usage in the field.
- **Custom `dd`/`partclone`-based tooling built from scratch** — maximum control, but reimplements a large amount of mature, already-solved functionality (multicast session management, PXE integration, partition-aware cloning) for no clear benefit.
- **Configuration-management-based provisioning** (e.g., Ansible/cloud-init driven installs per machine) — a fundamentally different model (install-and-configure rather than clone-a-golden-image) that doesn't match the "identical classroom of physically similar machines" use case as directly, and would push build-time customisation logic into deploy-time execution on every machine, working against `BLD-005` (reproducibility) rather than for it.

## Decision

Deploy will orchestrate **Clonezilla** as its underlying deployment engine (`PLAT-006`), using its existing multicast and PXE network-deployment capabilities rather than reimplementing them. Builder's output format is chosen to be Clonezilla/partclone-compatible specifically because of this decision (`BLD-003`).

## Consequences

- Deploy's scope is bounded to orchestration, scheduling, verification, and reporting around Clonezilla sessions — not to cloning/imaging internals, which remain Clonezilla's responsibility and benefit from its existing maturity and community support.
- BCS inherits Clonezilla's own platform support and limitations; if Clonezilla's NVMe/UEFI/GPT handling has gaps, those become BCS constraints too, and are tracked as platform requirements (`PLAT-003`–`PLAT-006`) rather than papered over.
- Technicians already familiar with Clonezilla from prior school-IT tooling have a shorter learning curve adopting BCS's Deploy component.
- If Clonezilla's project health, licensing, or capabilities change materially in the future, revisiting this decision means writing a superseding ADR — this document is the record of why it was chosen, not a guarantee it can never change.
