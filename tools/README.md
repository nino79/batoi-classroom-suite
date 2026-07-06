# tools/

Developer tooling to support working on BCS components (distinct from [scripts/](../scripts/), which covers repository/CI housekeeping, and from the components themselves in [boot-manager/](../boot-manager/), [builder/](../builder/), [deploy/](../deploy/)).

## Status

Empty placeholder. No tooling is implemented yet — BCS is currently in its [documentation-only phase](../ROADMAP.md).

## Anticipated Contents

- Local test-hardware/VM helpers for exercising Boot Manager's UEFI boot menu without physical classroom machines.
- A validator that checks `ClassroomConfig` YAML files against [config/schema.yaml](../config/schema.yaml) (see [docs/CONFIGURATION.md](../docs/CONFIGURATION.md)) — the schema is defined; this tooling is not implemented yet.
- Local PXE/multicast test-harness tooling for Deploy, to exercise deployment sessions without a full classroom.
