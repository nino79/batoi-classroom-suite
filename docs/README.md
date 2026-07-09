# BCS Documentation

This directory contains the detailed documentation for Batoi Classroom Suite (BCS). The top-level [ARCHITECTURE.md](../ARCHITECTURE.md) and [SPECIFICATION.md](../SPECIFICATION.md) are the normative entry points; everything here expands on them per component.

## Contents

| Section | Purpose |
|---|---|
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | Single-page dashboard answering "what is implemented today," generated from repository state — not a substitute for [ROADMAP.md](../ROADMAP.md) or [CHANGELOG.md](../CHANGELOG.md). |
| [PATTERNS.md](PATTERNS.md) | The canonical, repeatable implementation methodology for Platform Layer adapters — lifecycle, Definition of Done, testing strategy, architecture rules, and a mechanical checklist for building the next one (Filesystem, Network, CPU, Memory, TPM, or any future adapter). |
| [architecture/](architecture/) | Per-component architecture deep-dives: responsibilities, internal design, interfaces, Mermaid diagrams. |
| [specifications/](specifications/) | Per-component functional requirements, expanding [SPECIFICATION.md](../SPECIFICATION.md). |
| [decisions/](decisions/) | Architecture Decision Records (ADRs) — the durable "why" behind hard-to-reverse choices. |
| [standards/](standards/) | Coding, Bash, Markdown, and naming conventions. |
| [processes/](processes/) | Development workflow and release process. |
| [guides/](guides/) | Practical, contributor-facing guides: getting started, FAQ. |
| [glossary.md](glossary.md) | Definitions for domain terms (LliureX, UEFI, ESP, Clonezilla, etc.) used throughout the docs. |
| [repository-organization.md](repository-organization.md) | Canonical explanation of the whole repository's folder structure. |
| [VM_DEMO_GUIDE.md](VM_DEMO_GUIDE.md) | Step-by-step guide for running `bcs` on a fresh Ubuntu 24.04 VirtualBox VM — VM creation, OS install, BCS setup, and demo commands. |
| [VM_CHECKLIST.md](VM_CHECKLIST.md) | Printable pre-demo and during-demo verification checklist for every working `bcs` command, edge case, and cleanup step. |
| [MVP_DEMO_PLAN.md](MVP_DEMO_PLAN.md) | Scripted 20-25 minute demo presentation covering context, install, basic commands, validate, inventory, doctor, architecture, and stubs. |
| [HARDWARE_MATRIX.md](HARDWARE_MATRIX.md) | Hardware/software requirements and compatibility for every Platform Layer adapter and Host Inventory collector, including VM support. |
| [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) | Documented, accepted gaps and limitations in the Phase 0 CLI implementation, each linked to its owning design doc or ADR. |
| [VM_FIRST_BOOT.md](VM_FIRST_BOOT.md) | Protocol for creating a Ubuntu 24.04 VM from scratch in VirtualBox — install steps, EFI/NVMe config, network, and initial snapshot. |
| [VM_INSTALLATION.md](VM_INSTALLATION.md) | Exact copy-paste commands to install `bcs` on a fresh Ubuntu 24.04 VM — apt, clone, venv, pip install. |
| [VM_VALIDATION.md](VM_VALIDATION.md) | Structured validation checklist with 27 test cases — each with objective, command, expected result, and PASS/FAIL fields. |
| [VM_BUG_REPORT_TEMPLATE.md](VM_BUG_REPORT_TEMPLATE.md) | Bug report template for issues found during VM validation — hardware, VirtualBox, Ubuntu versions, command, output, logs, priority. |
| [VM_TEST_LOG.md](VM_TEST_LOG.md) | Empty test journal for recording validation sessions, test results, and bugs found. |
| [REAL_WORLD_VALIDATION.md](REAL_WORLD_VALIDATION.md) | Permanent historical record of the first `bcs` execution outside CI (Ubuntu 24.04, VirtualBox, SATA) — environment, commands, results, and the integration gap it surfaced. |
| [ISSUE_70_IMPLEMENTATION_CHECKLIST.md](ISSUE_70_IMPLEMENTATION_CHECKLIST.md) | Working implementation checklist for [issue #70](https://github.com/nino79/batoi-classroom-suite/issues/70) — atomic tasks, ADR review, test-suite impact, and risk assessment. |
| [BETA_VALIDATION_PLAN.md](BETA_VALIDATION_PLAN.md) | Structured validation process and exit criteria for the Beta phase — purpose, scope, goals, supported environments, bug classification, and regression policy. |
| [BETA_ROADMAP.md](BETA_ROADMAP.md) | Development roadmap for the Beta phase — 7 milestones (storage fix, HDO integration, Network Adapter wiring, Secure Boot fix, physical validation, infrastructure, release), with effort estimates, dependencies, and collector deprecation plan. |
| [HARDWARE_VALIDATION_MATRIX.md](HARDWARE_VALIDATION_MATRIX.md) | Expected `bcs` behaviour across every supported environment — VirtualBox, physical Ubuntu 24.04, Debian 12, LliureX 23, Secure Boot on/off, NVMe/SATA/USB storage. |
| [BETA_RELEASE_CHECKLIST.md](BETA_RELEASE_CHECKLIST.md) | Pre-release verification checklist covering installation, CLI startup, validation, inventory, doctor, JSON, YAML, performance, regression, and hardware validation. |
| [LEGACY_COLLECTOR_DEPRECATION_PLAN.md](LEGACY_COLLECTOR_DEPRECATION_PLAN.md) | Deprecation roadmap for the legacy host-inventory collectors (`collectors.py`) — fate of every function, dual-read safety rules, test migration plan, removal conditions, and rollback procedures. |
| [LEGACY_COLLECTOR_MIGRATION_AUDIT.md](LEGACY_COLLECTOR_MIGRATION_AUDIT.md) | Post-issue-#70 audit of every remaining legacy collector, every `HostDiscoverySnapshot` field, and every code path bypassing the Host Discovery Orchestrator — with per-function migration roadmap, dependency graph, sprint plan, and technical debt register. |
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
