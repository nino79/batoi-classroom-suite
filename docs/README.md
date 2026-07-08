# BCS Documentation

This directory contains the detailed documentation for Batoi Classroom Suite (BCS). The top-level [ARCHITECTURE.md](../ARCHITECTURE.md) and [SPECIFICATION.md](../SPECIFICATION.md) are the normative entry points; everything here expands on them per component.

## Contents

| Section | Purpose |
|---|---|
| [architecture/](architecture/) | Per-component architecture deep-dives: responsibilities, internal design, interfaces, Mermaid diagrams. |
| [specifications/](specifications/) | Per-component functional requirements, expanding [SPECIFICATION.md](../SPECIFICATION.md). |
| [decisions/](decisions/) | Architecture Decision Records (ADRs) — the durable "why" behind hard-to-reverse choices. |
| [standards/](standards/) | Coding, Bash, Markdown, and naming conventions. |
| [processes/](processes/) | Development workflow and release process. |
| [guides/](guides/) | Practical, contributor-facing guides: getting started, FAQ. |
| [glossary.md](glossary.md) | Definitions for domain terms (LliureX, UEFI, ESP, Clonezilla, etc.) used throughout the docs. |
| [repository-organization.md](repository-organization.md) | Canonical explanation of the whole repository's folder structure. |
| [CONFIGURATION.md](CONFIGURATION.md) | The unified YAML configuration format (`config/schema.yaml`) that drives Boot Manager, Builder, and Deploy. |
| [CLI.md](CLI.md) | Complete design of `bcs`, the command-line interface into all three components. |
| [HOST_INVENTORY.md](HOST_INVENTORY.md) | Design (see [ADR-0008](decisions/0008-host-inventory-ports-and-adapters.md), Accepted) for the Host Inventory subsystem — the single source of truth describing the current machine, consumed by `bcs doctor`, `bcs inventory`, and future Boot Manager/Builder/Deploy/REST API/Web UI. |
| [PLATFORM_LAYER.md](PLATFORM_LAYER.md) | Design (see [ADR-0009](decisions/0009-platform-layer-command-runner.md), Accepted; core and `RuntimeContext` wiring implemented) for the Platform Layer — the `CommandRunner` abstraction that centralizes every OS process execution in `cli/`, so business code never calls `subprocess` directly. |
| [EFI_ADAPTER.md](EFI_ADAPTER.md) | Design (see [ADR-0010](decisions/0010-efi-adapter-read-only-scope.md), Accepted; fully implemented) for the EFI Adapter (`bcs.platform.adapters.efi`) — a read-only firmware boot configuration wrapper, the first Host Discovery adapter built on the Platform Layer. |
| [STORAGE_ADAPTER.md](STORAGE_ADAPTER.md) | Design (Accepted; fully implemented) for the Storage Adapter (`bcs.platform.adapters.storage`) — a read-only block/partition/filesystem topology wrapper, the second Host Discovery adapter. |
| [SECURE_BOOT_ADAPTER.md](SECURE_BOOT_ADAPTER.md) | Design (Accepted; fully implemented) for the Secure Boot Adapter (`bcs.platform.adapters.secureboot`) — a read-only firmware Secure Boot state wrapper, the third Host Discovery adapter. |
| [HOST_DISCOVERY_ORCHESTRATOR.md](HOST_DISCOVERY_ORCHESTRATOR.md) | Design (see [ADR-0011](decisions/0011-host-discovery-orchestrator.md), Accepted; implemented, including `RuntimeContext`/composition-root wiring) for the Host Discovery Orchestrator — coordinates every Host Discovery adapter into one snapshot consumed by Host Inventory. |

## Reading Order

If you're new to the project, read in this order:

1. [README.md](../README.md) — what BCS is and why it exists.
2. [ARCHITECTURE.md](../ARCHITECTURE.md) — the system design.
3. [SPECIFICATION.md](../SPECIFICATION.md) — the requirements.
4. [glossary.md](glossary.md) — as needed, for unfamiliar terms.
5. [guides/getting-started.md](guides/getting-started.md) — how to get involved.
6. [processes/development-workflow.md](processes/development-workflow.md) and [standards/](standards/) — before your first pull request.

For the reasoning behind specific architectural choices, see [decisions/](decisions/) rather than re-deriving it from the architecture document alone.
