# Testing Infrastructure

**Status:** Accepted · **Last updated:** 2026-07-09

## Shared `FakeCommandRunner`

A consolidated `FakeCommandRunner` + `build_command_result` helper lives at `cli/tests/fake_command_runner.py` and replaces the seven duplicated `FakeCommandRunner` + `FakeCommandResult` + `_make_result` triples that previously existed across every adapter test file.

### Design

- Returns real `CommandResult` objects (not `MagicMock`)
- Two modes:
  - **Single-result mode** — pass `result`; the same `CommandResult` is returned on every `run()` call. Used by EFI, Secure Boot, Filesystem, and Network adapter tests.
  - **Multi-tool mode** — pass `results` (`dict[str, CommandResult]`), keyed by `command[0]` (the tool name). Used by Storage adapter and pipeline tests.
- Error simulation via `not_found_tools` and `timeout_tools`: named tools raise `CommandNotFoundError` or `CommandTimeoutError` respectively, checked before result lookup.
- Every call is recorded in `calls` with full argument snapshots (`command`, `timeout_seconds`, `check`, `cwd`, `env`, `input_text`).
- Satisfies `isinstance(runner, CommandRunner)` against the `@runtime_checkable` protocol.

### Migration

1. Replace local `FakeCommandResult`/`FakeCommandRunner`/`_make_result` with imports from `tests.fake_command_runner`.
2. Replace `_make_result(...)` calls with `build_command_result(...)`.
3. Replace `FakeCommandRunner(raise_not_found=True)` with `FakeCommandRunner(not_found_tools=frozenset({"toolname"}))`.
4. Replace `FakeCommandRunner(raise_timeout=True)` with `FakeCommandRunner(timeout_tools=frozenset({"toolname"}))`.
5. Replace `FakeCommandRunner(result=FakeCommandResult(...))` with `FakeCommandRunner(result=build_command_result(...))`.

### Migrated Files

| File | Mode | Status |
|------|------|--------|
| `cli/tests/fake_command_runner.py` | — (shared infrastructure) | ✅ |
| `cli/tests/test_platform_adapters_efi_adapter.py` | Single-result | ✅ Migrated |
| `cli/tests/test_platform_adapters_secureboot_adapter.py` | Single-result | ✅ Migrated |
| `cli/tests/test_platform_adapters_filesystem_adapter.py` | Single-result | ✅ Migrated |
| `cli/tests/test_platform_adapters_network_adapter.py` | Single-result | ✅ Migrated |
| `cli/tests/test_platform_adapters_storage_adapter.py` | Multi-tool | ✅ Migrated |
| `cli/tests/test_host_discovery_pipeline.py` | Multi-tool | ✅ Migrated |

### NOT Migrated (intentionally)

The four error test files (`test_platform_adapters_{storage,secureboot,filesystem,network}_errors.py`) build real `CommandResult` objects directly to test error class behaviour. They do not use `FakeCommandRunner` and were never candidates for migration.

### LOC Reduction

| Metric | Before | After |
|--------|--------|-------|
| `FakeCommandResult` classes | 6 | 0 (1 shared) |
| `FakeCommandRunner` classes | 6 | 0 (1 shared) |
| `_make_result` functions | 6 | 0 (1 shared `build_command_result`) |
| Test helper boilerplate | ~420 lines | ~42 lines (+ docstrings) |
