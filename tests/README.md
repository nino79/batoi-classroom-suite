# tests/

Cross-component test strategy for BCS. Component-specific tests will live alongside each component's implementation (`boot-manager/`, `builder/`, `deploy/`); this directory is for tests that span component boundaries.

## Status

Empty placeholder. No tests are implemented yet — BCS is currently in its [documentation-only phase](../ROADMAP.md).

## Anticipated Contents

Once implementation begins (see [ROADMAP.md](../ROADMAP.md)), this directory is expected to hold integration tests validating the interfaces described in [ARCHITECTURE.md §4](../ARCHITECTURE.md#4-component-boundaries):

- **Builder → Deploy:** a golden image artifact produced by Builder is accepted and correctly verified by Deploy (`BLD-002`/`BLD-006` ↔ `DEP-004`).
- **Deploy → Boot Manager:** a disk layout restored by Deploy is correctly discovered and booted by Boot Manager (`DEP-003` ↔ `BM-001`–`BM-002`).
- **Boot Manager → Deploy:** a maintenance request issued by Boot Manager is correctly received and actioned by Deploy (`BM-006` ↔ `DEP-006`).
- **End-to-end:** the full lifecycle in [docs/architecture/overview.md](../docs/architecture/overview.md#the-classroom-pc-lifecycle), from recipe to booted classroom, exercised against real or virtualised UEFI/NVMe hardware.

Per [NFR-005](../SPECIFICATION.md#3-non-functional-requirements), each component must also remain testable independently — those tests live with the component, not here.
