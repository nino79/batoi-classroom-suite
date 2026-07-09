# Real-World Validation — First Execution Outside CI

This document is the permanent historical record of the **first time `bcs` was executed on a real machine outside of CI/unit tests**. Everything before this run had only ever been verified against `FakeCommandRunner` test doubles, `SubprocessCommandRunner` invoking the test interpreter itself, or GitHub Actions' own `ubuntu-latest` runners (`.github/workflows/ci.yml`'s `cli-smoke-test` job) — never a machine resembling the actual target platform (`SPECIFICATION.md` `PLAT-001`–`PLAT-007`).

This is a point-in-time record, not a living document — it is not updated as later fixes land. Ongoing validation sessions belong in `docs/VM_TEST_LOG.md`; forward-looking validation planning belongs in `docs/BETA_VALIDATION_PLAN.md`/`docs/VM_VALIDATION.md`. Outstanding work this run surfaced is tracked in GitHub issues, not here.

## Tested Environment

| Property | Value |
|---|---|
| Hypervisor | VirtualBox |
| Guest OS | Ubuntu 24.04 LTS |
| Firmware | UEFI enabled |
| Storage controller | Intel 82801HM AHCI (SATA) |
| Disk device (as seen by Linux) | `/dev/sda` |
| Disk enumeration tool | `lsblk` — correctly reported the disk and its partitions |

This is **not** the NVMe-controller configuration `docs/VM_FIRST_BOOT.md`/`cli/README.md` document for a "clean `bcs doctor`" demo — it is a SATA-controller VM, which is exactly what surfaced the finding below. Both configurations are legitimate to validate against: NVMe exercises the `PLAT-005`-primary path end to end; SATA exercises the `PLAT-005`-secondary ("best-effort") path and, as it turned out, an integration gap that the NVMe configuration would not have revealed on its own.

## Commands Executed

```bash
bcs --help
bcs version
bcs validate
bcs doctor
bcs inventory
bcs inventory --output json
```

## Results

| Command | Result |
|---|---|
| `bcs --help` | ✅ Succeeded |
| `bcs version` | ✅ Succeeded |
| `bcs validate` | ✅ Succeeded |
| `bcs doctor` | ✅ Succeeded (ran to completion; per-check pass/warn/fail as expected for this environment — see `docs/KNOWN_LIMITATIONS.md`) |
| `bcs inventory` | ⚠️ Succeeded but with a discovered limitation — see below |
| `bcs inventory --output json` | ⚠️ Succeeded but with the same discovered limitation |

## Successful Behaviours

- The full install path (`apt install python3-venv git` → clone → `python3 -m venv` → `pip install -e ".[dev]"`) worked end to end on a genuinely clean Ubuntu 24.04 install.
- `bcs` did not crash, hang, or raise an unhandled exception on any of the six commands.
- `bcs --help`/`version`/`validate`/`doctor` produced output consistent with CI's own `cli-smoke-test` expectations.
- `bcs doctor` correctly evaluated per-check pass/warn/fail without crashing, including checks that legitimately fail on this specific hardware profile (per `SPECIFICATION.md` `PLAT-003`–`PLAT-005`).
- All four fully-implemented Platform Layer adapters (EFI, Storage, Secure Boot, Filesystem) executed correctly where exercised — this run validated that the Platform Layer itself (`CommandRunner`, locale forcing, error mapping, the adapters' own parsers) works against real tool output on a real kernel, not just synthetic fixtures.

## Discovered Limitation

`bcs inventory` (both text and `--output json`) reported an **empty `storage` array**, despite `lsblk` on the same machine correctly showing `/dev/sda` and its partitions.

**Root cause** (full trace in issue [#70](https://github.com/nino79/batoi-classroom-suite/issues/70)):

- `bcs.inventory.collectors.collect_storage()` (`cli/src/bcs/inventory/collectors.py:95-102`) intentionally enumerates only `/dev/nvme[0-9]n[0-9]`, per `SPECIFICATION.md` `PLAT-005` ("primary supported storage medium is NVMe"). This has been unchanged since the very first commit that introduced it — **not a regression**.
- The Storage Adapter (`bcs.platform.adapters.storage`) already enumerates the complete device topology via `lsblk`/`blkid`/`findmnt`, with no NVMe filtering — `is_nvme` on its `BlockDevice` model is a descriptive fact, not a filter. On this exact machine, the Storage Adapter would have reported `/dev/sda` correctly.
- The Host Discovery Orchestrator that coordinates the Storage Adapter is fully implemented and wired into `RuntimeContext` on every invocation, but `bcs.commands.inventory.run_inventory()` never passes it into `collect_host_inventory()` — a known, previously-theoretical limitation (`docs/KNOWN_LIMITATIONS.md`, `docs/HOST_DISCOVERY_ORCHESTRATOR.md`'s own status banner) that this run gave its first concrete, user-visible symptom.

**This is not a Storage Adapter defect.** It is an architectural integration gap between the CLI inventory pipeline and the already-validated Platform Layer — tracked in issue [#70](https://github.com/nino79/batoi-classroom-suite/issues/70) (the concrete fix) and issue [#78](https://github.com/nino79/batoi-classroom-suite/issues/78) (the full phased plan this fits into).

## Conclusions

1. **The Platform Layer is validated on real hardware, not just in CI.** `CommandRunner`, the locale policy, and all four adapters' parsing/error-mapping logic have now been exercised against a real Linux kernel and real tool output, not only `FakeCommandRunner` doubles and GitHub Actions runners.
2. **The remaining Phase 0 work in this area is integration, not adapter implementation.** No adapter needs new code to pass this kind of validation; what's missing is wiring already-built, already-tested components together — see issues #70 and #78.
3. **Documentation-described environment setup (EFI/NVMe) and validated-in-practice environment setup (EFI/SATA) both matter.** This run's SATA configuration, though not the documented "clean doctor run" configuration, was exactly what was needed to surface a real gap the NVMe configuration would have masked.
4. **No code was changed as a result of this run.** Per project convention, findings were converted directly into tracked issues (#70, #78) rather than an ad hoc fix — see `AGENTS.md § Workflow`.

## Next Milestone

Close issue [#70](https://github.com/nino79/batoi-classroom-suite/issues/70) (wire the orchestrator into the inventory pipeline for `storage`, with the `BlockDevice`→`StorageDevice` translation it requires), then re-run this exact validation on the same SATA-controller VM configuration to confirm `bcs inventory` reports the disk. Once that closes, extend validation to the NVMe-controller configuration documented in `docs/VM_FIRST_BOOT.md` to confirm parity across both supported storage paths before treating any Phase 0 CLI surface as Beta-ready (see `docs/BETA_VALIDATION_PLAN.md`).
