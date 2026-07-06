# Specification

This document defines the functional and non-functional requirements of Batoi Classroom Suite (BCS). It is the normative reference for what each component must do; [ARCHITECTURE.md](ARCHITECTURE.md) explains how they do it and why they are shaped this way.

Requirements are identified so they can be referenced from issues, pull requests, and ADRs (e.g. `PLAT-001`, `BM-004`).

## 1. Target Platform Matrix

BCS is intentionally scoped to a specific, concrete platform rather than generic hardware/OS support. Anything outside this matrix is out of scope unless explicitly added to the roadmap.

| ID | Requirement |
|---|---|
| PLAT-001 | The supported guest operating system is **LliureX 23**. |
| PLAT-002 | LliureX 23 in this project targets **Ubuntu 24.04 LTS** as its base distribution. |
| PLAT-003 | The only supported firmware interface is **UEFI**. Legacy BIOS/CSM boot is not supported. |
| PLAT-004 | UEFI **Secure Boot** must be either supported or safely, explicitly disabled as part of deployment — silent incompatibility is not acceptable. |
| PLAT-005 | The primary supported storage medium is **NVMe** (M.2, `/dev/nvme*`). SATA SSD may work but is best-effort, not a supported target for v1.0. |
| PLAT-006 | The deployment engine is **Clonezilla** (Live and/or Server Edition, as appropriate per component). |
| PLAT-007 | The deployment context is a **wired classroom LAN** capable of PXE network boot and IP multicast. Wireless-only or unmanaged/consumer networks are out of scope. |

## 2. Functional Requirements

### 2.1 Boot Manager

| ID | Requirement |
|---|---|
| BM-001 | On power-on, Boot Manager MUST present within a bounded time either a boot menu or an automatic default boot, configurable per deployment. |
| BM-002 | Boot Manager MUST support at minimum two boot paths: (a) normal boot into the installed LliureX 23 system, (b) maintenance boot that hands control to Deploy. |
| BM-003 | Boot Manager MUST manage UEFI NVRAM boot entries required for its own menu to appear reliably across reboots and firmware quirks. |
| BM-004 | Boot Manager's menu and branding MUST be themeable using assets from [`assets/`](assets/) (logos, icons, backgrounds, fonts) without code changes. |
| BM-005 | If Boot Manager's own configuration is missing, unreadable, or invalid, it MUST fall back to booting the installed OS directly rather than leaving the machine unusable. |
| BM-006 | Boot Manager MUST be able to issue a maintenance/re-imaging request identifying the local machine to Deploy (see interface in [ARCHITECTURE.md §4](ARCHITECTURE.md#4-component-boundaries)). |
| BM-007 | Boot Manager's UI text MUST support Valencian and Spanish, with English used for underlying code, configuration keys, and documentation. |

### 2.2 Builder

| ID | Requirement |
|---|---|
| BLD-001 | Builder MUST accept a declarative recipe describing package sets, configuration, and branding for a golden image. The recipe format is defined in [docs/CONFIGURATION.md](docs/CONFIGURATION.md). |
| BLD-002 | Builder MUST produce a versioned image artifact, with the version traceable to the recipe and base OS versions used to build it. |
| BLD-003 | Builder MUST produce output in a format Deploy can consume via Clonezilla (partclone-compatible partition images). |
| BLD-004 | Builder MUST lay out the target disk image with a UEFI-compatible partition scheme (GPT + ESP) suitable for NVMe targets. |
| BLD-005 | Given the same recipe and the same pinned input versions, Builder SHOULD produce a reproducible image (same package set and configuration, modulo build timestamps). |
| BLD-006 | Builder MUST record build provenance: recipe version, base OS version, build date, and a checksum of the resulting artifact. |

### 2.3 Deploy

| ID | Requirement |
|---|---|
| DEP-001 | Deploy MUST be able to image a single machine (unicast) and a full classroom (multicast) from the same golden image artifact. |
| DEP-002 | Deploy MUST support PXE network boot as an entry point into a deployment session, requiring no local bootable media. |
| DEP-003 | Deploy MUST restore the disk layout expected by Boot Manager, including the ESP and any recovery partition, on NVMe targets. |
| DEP-004 | Deploy MUST verify deployed images against the artifact's checksum and report success/failure per machine. |
| DEP-005 | Deploy MUST produce a session report (which machines, which image version, timing, outcome) suitable for a single technician auditing a classroom rollout. |
| DEP-006 | Deploy MUST accept maintenance/re-imaging requests originating from Boot Manager (BM-006) and schedule or execute them. |
| DEP-007 | A full-classroom multicast deployment of the reference classroom size (see NFR-002) SHOULD complete within a single class period. |

### 2.4 CLI

The `bcs` command-line interface is the single operator entry point into Boot Manager, Builder, and Deploy — see [ARCHITECTURE.md §8](ARCHITECTURE.md#8-operator-interface). Unlike the three components, its detailed design is not split across separate architecture/specification documents: [docs/CLI.md](docs/CLI.md) is the single, complete expansion of this section, by deliberate choice — see its introduction for why.

| ID | Requirement |
|---|---|
| CLI-001 | `bcs` MUST provide these top-level commands: `doctor`, `validate`, `inventory`, `build`, `install`, `deploy`, `backup`, `restore`, `update`, `version`, `config`. |
| CLI-002 | Every command MUST support `--help`; invoking `bcs` with no command, or an unrecognized one with no matching plugin, MUST print top-level help and exit with code `2`. |
| CLI-003 | `bcs` MUST support a consistent set of global options (see [docs/CLI.md](docs/CLI.md#global-options)) applied uniformly across all commands where applicable. |
| CLI-004 | `bcs` MUST use a single, documented exit code scheme shared by every command, not a bespoke scheme per command (see [docs/CLI.md](docs/CLI.md#exit-codes)). |
| CLI-005 | `bcs` MUST write command result data to stdout and logs/diagnostics/progress to stderr, so stdout remains scriptable independent of verbosity. |
| CLI-006 | Destructive operations (`install`, `deploy`, `restore`) MUST require explicit confirmation, or `--yes`, before proceeding, unless `--dry-run` is given. |
| CLI-007 | `bcs` MUST validate a loaded ClassroomConfig before `build`, `install`, `deploy`, or `restore` proceed, and MUST abort on failure (see `BLD-001`, [docs/CONFIGURATION.md](docs/CONFIGURATION.md)). |
| CLI-008 | `bcs` MUST resolve its ClassroomConfig via a documented precedence and MUST refuse to guess when no config can be unambiguously resolved, rather than silently operating against the wrong classroom. |
| CLI-009 | `bcs` MUST support loading external subcommands as plugins; built-in commands MUST always take precedence over a like-named plugin. |
| CLI-010 | `bcs` MUST NOT transmit telemetry or usage analytics; its only network calls are those explicitly implied by the invoked command. |
| CLI-011 | New commands, flags, and output fields MUST be additive within a `bcs` MAJOR version; breaking changes require a MAJOR version bump (see [docs/processes/release-process.md](docs/processes/release-process.md)). |
| CLI-012 | Machine-readable output (`--output json`) MUST include a `schemaVersion` field so scripts can detect changes across `bcs` versions. |
| CLI-013 | `bcs` MUST support composable verbosity controls (`-v`/`-q`/`--log-level`) with a documented precedence. |
| CLI-014 | Color output MUST default to auto-detection (TTY and `NO_COLOR` unset) and MUST be overridable via flags and environment variables. |
| CLI-015 | `bcs` MUST expose a versioned, immutable Host Inventory snapshot (`bcs inventory`) as the single source of truth describing the current machine; Boot Manager, Builder, and Deploy MUST consume the identical JSON shape, never a bespoke re-probe of the same facts. |
| CLI-016 | The Host Inventory snapshot (`CLI-015`) MUST report the EFI System Partition's presence, device/partition, filesystem, mount state, and size (see `BLD-004`, `DEP-003`), and MUST enumerate USB storage devices suitable for booting or deployment; it MUST NOT enumerate generic USB peripherals (keyboards, mice, webcams, hubs). |

## 3. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-001 | **Reliability.** Deployment operations MUST be safely resumable/retryable after a network interruption or a single machine's failure, without corrupting the session for other machines. |
| NFR-002 | **Performance.** The reference classroom size for performance targets is 20–30 machines on a single switch. |
| NFR-003 | **Security.** No golden image may embed long-lived, shared administrative credentials; secrets required at deploy time must be injected at deployment time, not baked into the image. See [SECURITY.md](SECURITY.md). |
| NFR-004 | **Auditability.** Every deployment session and every boot-manager-triggered maintenance action MUST be attributable to a machine and timestamped. |
| NFR-005 | **Maintainability.** Each component MUST be operable and testable independently of the other two, per the boundaries in [ARCHITECTURE.md](ARCHITECTURE.md). |
| NFR-006 | **Localisation.** User-facing text MUST support Valencian and Spanish; all code, identifiers, and documentation are in English. |
| NFR-007 | **Idempotency.** Re-running a deployment against a machine already at the target image version MUST be safe and MUST NOT be required to complete normal operation. |

## 4. Explicit Non-Goals

- Support for non-UEFI (legacy BIOS) machines.
- Support for spinning hard disks or non-NVMe SSDs as a primary, supported target.
- General-purpose configuration management for arbitrary (non-classroom) fleets.
- Replacing Clonezilla's cloning engine with a custom implementation.
- Managing curriculum or educational content — BCS deploys whatever the Builder recipe specifies.

## 5. Traceability

Detailed, component-level specifications expand on the requirements above:

- [docs/specifications/platform-requirements.md](docs/specifications/platform-requirements.md)
- [docs/specifications/boot-manager.md](docs/specifications/boot-manager.md)
- [docs/specifications/builder.md](docs/specifications/builder.md)
- [docs/specifications/deploy.md](docs/specifications/deploy.md)
- [docs/CLI.md](docs/CLI.md) — for `2.4 CLI`; combines the architecture and specification-detail layers the other three components keep separate (a deliberate exception, explained in that document's introduction).

Changes to requirements in this document should be accompanied by an ADR when they represent a scope or architectural change (see [docs/decisions/README.md](docs/decisions/README.md)) and reflected in [ROADMAP.md](ROADMAP.md).
