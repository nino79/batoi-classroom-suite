# scripts/

Maintainer, CI helper, and Beta validation scripts (repository housekeeping — not BCS component implementation, which lives in [boot-manager/](../boot-manager/), [builder/](../builder/), and [deploy/](../deploy/)).

## Contents

| Script | Purpose |
|--------|---------|
| `validate-beta.sh` | Orchestrate Beta validation — environment capture, CLI command execution, report generation. |
| `verify-environment.sh` | Collect host environment metadata (kernel, distribution, hypervisor, tools) as JSON. |
| `collect-artifacts.sh` | Archive all validation reports into a timestamped directory. |
| `hardware-validation/` | Reusable hardware capture, comparison, and summary scripts — see [toolkit docs](../docs/HARDWARE_VALIDATION_TOOLKIT.md). |

See [`docs/BETA_VALIDATION_AUTOMATION.md`](../docs/BETA_VALIDATION_AUTOMATION.md) for the Beta validation automation design, workflow, and CI integration guide.
See [`docs/HARDWARE_VALIDATION_TOOLKIT.md`](../docs/HARDWARE_VALIDATION_TOOLKIT.md) for the hardware validation toolkit reference.

## Future

- Documentation consistency checks (e.g., verifying cross-references between `SPECIFICATION.md` and `docs/specifications/*.md` stay in sync).
- `.github/LABELS.md` → GitHub label sync tooling.
- Release/versioning helpers once components reach implementation.
