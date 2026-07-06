# Deploy — Specification

This expands [SPECIFICATION.md §2.3](../../SPECIFICATION.md#23-deploy) with acceptance-level detail. Requirement IDs (`DEP-xxx`) remain owned by `SPECIFICATION.md`; this document adds the detail needed to design and later test against them. See [docs/architecture/deploy.md](../architecture/deploy.md) for the design rationale.

## Requirements Detail

### DEP-001 — Unicast and Multicast from One Artifact

- The same golden image artifact from Builder MUST be deployable to a single machine (unicast, e.g., for a maintenance-triggered re-image) and to a whole classroom at once (multicast), without producing a different artifact per mode.

### DEP-002 — PXE Network Boot Entry Point

- A machine MUST be able to enter a deployment session via PXE network boot alone — no USB stick, no local media preparation.
- This is also the mechanism Boot Manager's maintenance path (`BM-006`) is expected to trigger into.

### DEP-003 — Disk Layout Restoration

- Deploy MUST restore the full disk layout Builder produced (`BLD-004`): GPT, ESP, root filesystem, and any recovery partition, correctly on NVMe targets.
- The restored layout MUST be what Boot Manager expects to find at next boot (see [docs/architecture/boot-manager.md](../architecture/boot-manager.md)).

### DEP-004 — Verification Against Checksum

- After imaging, Deploy MUST verify the deployed image against the checksum recorded in Builder's provenance data (`BLD-006`).
- Verification result (pass/fail) MUST be part of the per-machine outcome in the session report (`DEP-005`).

### DEP-005 — Session Reporting

- Each deployment session MUST produce a report covering: which machines participated, which image version was deployed, timing, and per-machine outcome (including verification result from `DEP-004`).
- The report must be usable by a single technician auditing a classroom rollout without needing to inspect individual machine logs — this is the concrete form of `NFR-004` (auditability) for this component.

### DEP-006 — Maintenance Request Handling

- Deploy MUST accept a maintenance/re-imaging request identifying a machine (originating from Boot Manager, `BM-006`) and either execute it immediately (unicast) or schedule it into the next appropriate session.
- Exact transport/format is a joint open question with Boot Manager — see [docs/architecture/deploy.md](../architecture/deploy.md#open-questions).

### DEP-007 — Performance Target

- A full-classroom multicast deployment (reference size: 20–30 machines, `NFR-002`) SHOULD complete within a single class period.
- This is a "should," not a hard requirement, because network conditions vary by centre — but it is the design target that shapes multicast-first design (over per-machine unicast at scale).

## Non-Goals for This Component

- Deploy does not build images (that's Builder) — it consumes Builder's artifacts as-is.
- Deploy does not decide boot-time behavior after imaging completes (that's Boot Manager) beyond restoring the disk layout it expects.
- Deploy is not a general-purpose network provisioning tool for non-classroom fleets.
