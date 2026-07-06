# Glossary

Domain and technical terms used throughout BCS documentation, in alphabetical order.

**BCS** — Batoi Classroom Suite, this project.

**Boot Manager** — the BCS component that owns boot-time behaviour on each classroom machine. See [docs/architecture/boot-manager.md](architecture/boot-manager.md).

**Builder** — the BCS component that produces versioned golden images. See [docs/architecture/builder.md](architecture/builder.md).

**Classroom Fleet** — the set of physically similar machines in a single computer classroom, treated as the natural unit of a deployment session (see `NFR-002`).

**Clonezilla** — an open-source disk cloning/imaging tool, built on `partclone`, used by BCS's Deploy component as its underlying deployment engine (`PLAT-006`). See [ADR-0003](decisions/0003-clonezilla-as-deployment-engine.md).

**Deploy** — the BCS component that distributes golden images to a classroom fleet and verifies the result. See [docs/architecture/deploy.md](architecture/deploy.md).

**ESP (EFI System Partition)** — a FAT-formatted partition required by UEFI firmware to locate and launch bootloaders. BCS's disk layout requirements (`BLD-004`, `DEP-003`) centre on correctly building and restoring this partition on NVMe targets.

**Golden Image** — the versioned, checksummed disk image produced by Builder that represents "what a classroom PC should be." Deployed identically across a fleet by Deploy.

**GPT (GUID Partition Table)** — the partition table format required for UEFI boot, used instead of legacy MBR partitioning.

**LliureX** — the Valencian public education system's Linux distribution, maintained by the Conselleria d'Educació, and the target guest OS for BCS (`PLAT-001`).

**Maintenance Request** — the interface by which Boot Manager asks Deploy to (re-)image the requesting machine (`BM-006`/`DEP-006`). See [ARCHITECTURE.md §4](../ARCHITECTURE.md#4-component-boundaries).

**Multicast (IP Multicast)** — a network transmission mode allowing one sender (the Deploy server) to efficiently transmit an image to many receivers (a classroom of machines) simultaneously, rather than one connection per machine.

**NVMe** — Non-Volatile Memory Express, the primary supported storage interface for BCS target machines (`PLAT-005`), typically M.2 form-factor SSDs exposed as `/dev/nvme*`.

**partclone** — the underlying partition-cloning tool Clonezilla is built on; produces the partition image format Builder's output must be compatible with (`BLD-003`).

**PXE (Preboot Execution Environment)** — a standard allowing a machine to boot over the network without local media, used as the entry point into Deploy's deployment sessions (`DEP-002`).

**Recipe (Image Recipe / Manifest)** — the declarative description of package sets, configuration, and branding that Builder consumes to produce a golden image (`BLD-001`).

**Secure Boot** — a UEFI firmware feature that only allows cryptographically signed bootloaders/kernels to execute. A platform-level constraint on Boot Manager's design (`PLAT-004`).

**Session Report** — the per-deployment record Deploy produces, covering which machines participated, which image version, and per-machine outcome (`DEP-005`).

**Unicast** — a one-to-one network deployment mode, used for single-machine (re-)imaging as opposed to whole-classroom multicast (`DEP-001`).
