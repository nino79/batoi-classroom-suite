# Glossary

Domain and technical terms used throughout BCS documentation, in alphabetical order.

**BCS** — Batoi Classroom Suite, this project.

**Boot Manager** — the BCS component that owns boot-time behaviour on each classroom machine. See [docs/architecture/boot-manager.md](architecture/boot-manager.md).

**Builder** — the BCS component that produces versioned golden images. See [docs/architecture/builder.md](architecture/builder.md).

**Classroom Fleet** — the set of physically similar machines in a single computer classroom, treated as the natural unit of a deployment session (see `NFR-002`).

**ClassroomConfig** — the `kind` of the unified BCS configuration document (`apiVersion: bcs/v1alpha1`) that drives Boot Manager, Builder, and Deploy for one classroom. See [docs/CONFIGURATION.md](CONFIGURATION.md) and [config/schema.yaml](../config/schema.yaml).

**Clonezilla** — an open-source disk cloning/imaging tool, built on `partclone`, used by BCS's Deploy component as its underlying deployment engine (`PLAT-006`). See [ADR-0003](decisions/0003-clonezilla-as-deployment-engine.md).

**Deploy** — the BCS component that distributes golden images to a classroom fleet and verifies the result. See [docs/architecture/deploy.md](architecture/deploy.md).

**EFI Adapter** — BCS's read-only Platform Layer adapter for firmware boot configuration, `bcs.platform.adapters.efi` — domain-named rather than named after `efibootmgr`, the tool it currently wraps (see [docs/standards/naming-conventions.md § Domain-Driven Naming](standards/naming-conventions.md#domain-driven-naming)), so a future backend swap would not require a public rename. See [docs/EFI_ADAPTER.md](EFI_ADAPTER.md) and [ADR-0010](decisions/0010-efi-adapter-read-only-scope.md).

**efibootmgr** — the standard Linux tool for inspecting (and, in general, managing) UEFI NVRAM boot variables; BCS's EFI Adapter currently wraps it, read-only. See [docs/EFI_ADAPTER.md](EFI_ADAPTER.md) and [ADR-0010](decisions/0010-efi-adapter-read-only-scope.md).

**ESP (EFI System Partition)** — a FAT-formatted partition required by UEFI firmware to locate and launch bootloaders. BCS's disk layout requirements (`BLD-004`, `DEP-003`) centre on correctly building and restoring this partition on NVMe targets.

**Golden Image** — the versioned, checksummed disk image produced by Builder that represents "what a classroom PC should be." Deployed identically across a fleet by Deploy.

**GPT (GUID Partition Table)** — the partition table format required for UEFI boot, used instead of legacy MBR partitioning.

**Host Discovery** — the broader effort of read-only Platform Layer adapters that inspect the host system via external tools (starting with the EFI Adapter) rather than parsing `/proc`/`/sys` directly. See [docs/EFI_ADAPTER.md](EFI_ADAPTER.md).

**Host Inventory** — the immutable, versioned snapshot of a single machine's hardware/software facts (firmware, storage, network, identity, OS, CPU, memory, tooling), produced by `bcs inventory` and intended as the single source of truth consumed by `bcs doctor` and, eventually, Boot Manager, Builder, and Deploy. See [docs/HOST_INVENTORY.md](HOST_INVENTORY.md) and [ADR-0008](decisions/0008-host-inventory-ports-and-adapters.md).

**LliureX** — the Valencian public education system's Linux distribution, maintained by the Conselleria d'Educació, and the target guest OS for BCS (`PLAT-001`).

**Maintenance Request** — the interface by which Boot Manager asks Deploy to (re-)image the requesting machine (`BM-006`/`DEP-006`). See [ARCHITECTURE.md §4](../ARCHITECTURE.md#4-component-boundaries).

**Multicast (IP Multicast)** — a network transmission mode allowing one sender (the Deploy server) to efficiently transmit an image to many receivers (a classroom of machines) simultaneously, rather than one connection per machine.

**NVMe** — Non-Volatile Memory Express, the primary supported storage interface for BCS target machines (`PLAT-005`), typically M.2 form-factor SSDs exposed as `/dev/nvme*`.

**partclone** — the underlying partition-cloning tool Clonezilla is built on; produces the partition image format Builder's output must be compatible with (`BLD-003`).

**Platform Layer** — the part of BCS's Python code (`bcs.platform`) that centralizes every process execution (`subprocess`) behind a single `CommandRunner` interface, so business/command code never calls `subprocess` directly (`NFR-008`). See [docs/PLATFORM_LAYER.md](PLATFORM_LAYER.md) and [ADR-0009](decisions/0009-platform-layer-command-runner.md).

**PXE (Preboot Execution Environment)** — a standard allowing a machine to boot over the network without local media, used as the entry point into Deploy's deployment sessions (`DEP-002`).

**Recipe** — informal shorthand for the `spec.builder` and `spec.packages` sections of a ClassroomConfig document: the declarative description of package sets, configuration, and branding that Builder consumes to produce a golden image (`BLD-001`). See [docs/CONFIGURATION.md](CONFIGURATION.md). The term "manifest," used interchangeably with "recipe" in earlier drafts of this documentation, is retired — see [ADR-0005](decisions/0005-yaml-as-unified-configuration-format.md).

**Secure Boot** — a UEFI firmware feature that only allows cryptographically signed bootloaders/kernels to execute. A platform-level constraint on Boot Manager's design (`PLAT-004`).

**Session Report** — the per-deployment record Deploy produces, covering which machines participated, which image version, and per-machine outcome (`DEP-005`).

**Unicast** — a one-to-one network deployment mode, used for single-machine (re-)imaging as opposed to whole-classroom multicast (`DEP-001`).
