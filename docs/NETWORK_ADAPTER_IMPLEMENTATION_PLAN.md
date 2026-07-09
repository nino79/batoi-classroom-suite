# Network Adapter — Implementation Plan

> **Status: Accepted.** This document is the implementation plan for the
> Network Adapter, the fifth Host Discovery adapter in BCS's Platform
> Layer. It decomposes the remaining work (Parts 2–6; Part 1 — domain
> models — is already implemented) into discrete, independently
> verifiable parts following the same lifecycle
> [PATTERNS.md](PATTERNS.md) establishes for every adapter, and
> documented in [NETWORK_ADAPTER.md](NETWORK_ADAPTER.md) (Accepted).

## 1. Overview

### Implementation Scope

Complete the Network Adapter as designed in
[NETWORK_ADAPTER.md](NETWORK_ADAPTER.md). Part 1 (domain models) is
already implemented and **excluded** from this plan; Parts 2–6 cover
everything else.

### Expected Deliverables

| # | Deliverable | Depends on |
|---|-------------|------------|
| Part 2 | `errors.py` — the typed exception hierarchy | Nothing |
| Part 3 | `parser.py` — the pure function + fixtures | Models (Part 1) |
| Part 4 | `adapter.py` — the orchestration layer + `__init__.py` | Parts 2, 3 |
| Part 5 | Host Discovery typing + composition-root wiring | Part 4 |
| Part 6 | Repository-wide consistency pass | Parts 1–5 |

### Implementation Order

Recommended sequence: **Part 2 → Part 3 → Part 4 → Part 5 → Part 6**.
Parts 2 and 3 have no dependency on each other (see
[PATTERNS.md § 2](PATTERNS.md#2-adapter-lifecycle)'s note on ordering)
and could be built concurrently by separate agents; Parts 4, 5, and 6
are strictly sequential.

---

## 2. Breakdown into Implementation Parts

### Part 2 — Errors (`errors.py`)

#### Objective

Implement the `NetworkError`, `NetworkUnavailableError`, and
`NetworkParseError` exception hierarchy as designed in
[NETWORK_ADAPTER.md § Error Hierarchy](NETWORK_ADAPTER.md#error-hierarchy).

#### Files to Modify

- `cli/src/bcs/platform/adapters/network/__init__.py` — add imports for
  `NetworkError`, `NetworkUnavailableError`, `NetworkParseError`.
- `cli/src/bcs/platform/adapters/network/errors.py` — **create**.

#### Files That Must NOT Be Modified

- `cli/src/bcs/platform/adapters/network/models.py` — no changes needed.
- Any file outside `cli/src/bcs/platform/adapters/network/`.
- Any sibling adapter (EFI, Storage, Secure Boot, Filesystem).
- `bcs.app.main()`, `RuntimeContext`, `HostDiscoveryOrchestrator`.

#### Public API to Expose

```python
class NetworkError(PlatformError):            # base
    result: CommandResult | None

class NetworkUnavailableError(NetworkError):  # semantic: net data unavailable
class NetworkParseError(NetworkError):        # semantic: output unparseable
    text: str
```

Pattern follows every sibling adapter exactly:
- `NetworkError.__init__` accepts `message: str` and optional
  `result: CommandResult | None`, stored as `self.result`.
- `NetworkUnavailableError` adds no extra fields.
- `NetworkParseError.__init__` accepts `message: str` and
  `text: str`, stored as `self.text`.
- `from bcs.platform.errors import PlatformError`.
- `from bcs.platform.models import CommandResult` under `TYPE_CHECKING`.
- Docstrings name `docs/NETWORK_ADAPTER.md#error-hierarchy` and
  `docs/NETWORK_ADAPTER.md#error-mapping` as the authoritative design.

#### Tests to Add

| Test module | Verifies | Approach |
|---|---|---|
| `cli/tests/test_platform_adapters_network_errors.py` | `NetworkError` accepts/omits `result`; `NetworkUnavailableError` is a `NetworkError` and a `PlatformError`; `NetworkParseError` stores `text` and chains correctly; all three exported from `__init__.py`. | Direct unit tests, no fixtures or mocking — mirroring `test_platform_adapters_filesystem_errors.py`. |

#### Documentation to Update

- `docs/NETWORK_ADAPTER.md` — change the Error Hierarchy and Testing
  Strategy sections' "not yet implemented" markers to "[implemented]"
  for the error layer. Keep the parser/adapter rows as "not yet
  implemented."

#### Expected Quality Gates

- `ruff check` — clean.
- `ruff format --check` — clean.
- `mypy` — strict, clean across all 59+ source files.
- `pytest` — all existing tests + new tests pass.

#### Expected Coverage

- `cli/src/bcs/platform/adapters/network/errors.py` — 100% statement and
  branch coverage.

#### Definition of Done

- [ ] `errors.py` exists at the expected path with all three exception
  classes.
- [ ] Every exception has a docstring referencing the design document.
- [ ] `NetworkUnavailableError` is reachable as both
  `errors.NetworkUnavailableError` and `NetworkError` (via inheritance).
- [ ] All three names exported from `__init__.py` and listed in
  `__all__`.
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` — all green.
- [ ] `CHANGELOG.md` has an `[Unreleased]` entry for this part (see
  [Part 6](#part-6--repository-wide-consistency-pass) for the format).
- [ ] `docs/NETWORK_ADAPTER.md` status banner updated.

---

### Part 3 — Parser and Fixtures (`parser.py` + fixture corpus)

#### Objective

Implement the pure JSON parser `parse_network_interfaces(text: str) ->
NetworkInterfaceStatus` and scaffold the `cli/tests/fixtures/network/`
fixture corpus, both as designed in
[NETWORK_ADAPTER.md § Parser Strategy](NETWORK_ADAPTER.md#parser-strategy)
and [§ Fixtures Strategy](NETWORK_ADAPTER.md#fixtures-strategy).

#### Files to Modify

- `cli/src/bcs/platform/adapters/network/__init__.py` — add
  `parse_network_interfaces`.
- `cli/src/bcs/platform/adapters/network/parser.py` — **create**.
- `cli/tests/fixtures/network/README.md` — **create**.

#### Files to Create

- `cli/tests/fixtures/network/` — directory.
- `cli/tests/fixtures/network/ip_unknown_ubuntu-24.04_ethernet-up.txt` — zero-byte placeholder.
- `cli/tests/fixtures/network/ip_unknown_ubuntu-24.04_ethernet-down.txt` — zero-byte placeholder.
- `cli/tests/fixtures/network/ip_unknown_ubuntu-24.04_multi-interface.txt` — zero-byte placeholder.
- `cli/tests/fixtures/network/ip_unknown_ubuntu-24.04_ipv6-only.txt` — zero-byte placeholder.
- `cli/tests/fixtures/network/ip_unknown_ubuntu-24.04_no-address.txt` — zero-byte placeholder.
- `cli/tests/fixtures/network/ip_unknown_ubuntu-24.04_empty.txt` — zero-byte placeholder.
- `cli/tests/fixtures/network/ip_unknown_ubuntu-24.04_unavailable-stderr.txt` — zero-byte placeholder.

#### Files That Must NOT Be Modified

- `cli/src/bcs/platform/adapters/network/models.py` — depends on it but
  must not change it.
- `cli/src/bcs/platform/adapters/network/errors.py` — parser raises
  plain `ValueError` (see [PATTERNS.md § 6](PATTERNS.md#6-architecture-rules));
  never imports `errors.py`.
- Any sibling adapter.
- `bcs.app.main()`, `RuntimeContext`, `HostDiscoveryOrchestrator`.

#### Public API to Expose

```python
def parse_network_interfaces(text: str) -> NetworkInterfaceStatus: ...
```

Pure function. Returns exactly one `NetworkInterfaceStatus`. Raises
`ValueError` (never a `NetworkParseError` — that's `adapter.py`'s job):

- If the text is not valid JSON.
- If the top-level value is not a JSON array.
- If any array element is not a JSON object.
- If an entry has a missing or empty `ifname` field (malformed entry,
  quoting the 1-based entry index).

Does **not** raise for:
- An empty array `[]` — returns `NetworkInterfaceStatus(interfaces=())`.
- Unrecognized JSON fields — silently ignored.
- A missing `address` field — `mac_address = None`.
- A null-MAC address (`"00:00:00:00:00:00"`) — `mac_address = None`.
- A missing or non-array `addr_info` — `ip_addresses = ()`.
- Unexpected `addr_info[*]` fields — silently ignored.

Parsing logic:
1. `json.loads(text)` → list of dicts.
2. For each entry (1-indexed), extract fields per the JSON mapping
   table in [NETWORK_ADAPTER.md § Parser Strategy](NETWORK_ADAPTER.md#parser-strategy).
3. `flags` is expected as a list of strings; `is_up` requires both
   `"UP"` and `"LOWER_UP"`; `is_loopback` requires `"LOOPBACK"`.
4. `addr_info` entries filtered to `family in ("inet", "inet6")`;
   `local` values collected into a flat tuple in iteration order.

#### Tests to Add

| Test module | Verifies | Approach |
|---|---|---|
| `cli/tests/test_platform_adapters_network_parser.py` | Every JSON field shape individually and combined; permissive handling of unrecognized fields; absent `address`; null MAC; empty `addr_info`; absent `addr_info`; non-array `addr_info`; empty input (empty JSON array); multiple interfaces; IPv4 and IPv6 mixed; malformed entry (missing `ifname`) with its index-in-array error message; and — via AST inspection — the import-purity check. | Direct unit tests, using fixtures loaded via `fixture_utils.py`. Build a `tmp_path`-rooted synthetic corpus mirroring the real one's layout, exactly as `test_platform_adapters_efi_parser.py` did before real `efibootmgr` captures existed. |

#### Expected Quality Gates

Same as Part 2.

#### Expected Coverage

- `cli/src/bcs/platform/adapters/network/parser.py` — 100% statement
  and branch coverage.

#### Definition of Done

- [ ] `parser.py` exists at the expected path.
- [ ] `parse_network_interfaces` is a pure function (`text: str` in,
  `NetworkInterfaceStatus` out).
- [ ] Parser never imports `CommandRunner`, `subprocess`, `errors.py`,
  or `bcs.platform.execution`.
- [ ] AST-based import-purity test passes.
- [ ] `cli/tests/fixtures/network/` exists with a populated README
  (capture command, layout, naming, inventory table) and all six
  zero-byte placeholder scenario files.
- [ ] `__init__.py` re-exports `parse_network_interfaces` in `__all__`.
- [ ] All quality gates pass.
- [ ] `CHANGELOG.md` entry.
- [ ] `docs/NETWORK_ADAPTER.md` status banner updated.

---

### Part 4 — Adapter (`adapter.py` + package completion)

#### Objective

Implement `adapter.read_network_interfaces(runner: CommandRunner) ->
NetworkInterfaceStatus`, the orchestration layer that calls `ip -json
addr show`, wires parser + errors together, and completes the
`__init__.py` exports.

#### Files to Modify

- `cli/src/bcs/platform/adapters/network/__init__.py` — add
  `read_network_interfaces`.
- `cli/src/bcs/platform/adapters/network/adapter.py` — **create**.

#### Files That Must NOT Be Modified

- `cli/src/bcs/platform/adapters/network/models.py` — no changes.
- `cli/src/bcs/platform/adapters/network/parser.py` — no changes.
- `cli/src/bcs/platform/adapters/network/errors.py` — no changes.
- Any sibling adapter.
- `bcs.app.main()`, `HostDiscoveryAdapters`,
  `HostDiscoverySnapshot`, `RuntimeContext`.

#### Public API to Expose

```python
def read_network_interfaces(
    runner: CommandRunner,
    *,
    timeout_seconds: float | None = 5.0,
) -> NetworkInterfaceStatus: ...
```

Logic (per [NETWORK_ADAPTER.md § Adapter Responsibilities](NETWORK_ADAPTER.md#adapter-responsibilities)):

1. Build command: `["ip", "-json", "addr", "show"]`.
2. Build locale-forced env: `os.environ.copy()` + `LANG=C`/`LC_ALL=C`.
3. Call `runner.run(command, timeout_seconds=5.0, env=env, check=False)`.
4. On zero exit, pass `result.stdout` to `parser.parse_network_interfaces`.
5. If parser raises `ValueError`, wrap as `NetworkParseError(text=result.stdout)`.
6. On non-zero exit, check `result.stderr` against `_UNAVAILABLE_PATTERNS`
   (e.g. `"network namespace not accessible"`, `"permission denied"`,
   `"cannot open netlink socket"`) — raise `NetworkUnavailableError` if
   matched, `NetworkError(result=result)` otherwise.
7. `CommandNotFoundError`/`CommandTimeoutError` propagate unchanged.

The `_UNAVAILABLE_PATTERNS` frozenset mirrors every sibling adapter's
pattern. Concrete patterns to be determined during implementation from
real `ip` stderr observations; at minimum includes:
- `"cannot open netlink socket"`
- `"permission denied"`
- `"network is unreachable"` (defensive; `ip` should not exit non-zero
  for this on a running system, but the adapter degrades gracefully)

#### Tests to Add

| Test module | Verifies | Approach |
|---|---|---|
| `cli/tests/test_platform_adapters_network_adapter.py` | Correct command (`["ip", "-json", "addr", "show"]`); correct locale-forced `env` with `PATH` preserved; correct explicit `timeout_seconds` (including the `5.0` default and `None`); `check=False`; correct hand-off to parser; `NetworkParseError` wrapping (with `__cause__` preserved); `NetworkUnavailableError` for each recognised "unavailable" `stderr` pattern; `NetworkError` for unrecognised non-zero exit; `CommandNotFoundError`/`CommandTimeoutError` propagated unchanged. | `FakeCommandRunner` programmed to return/raise each shape. |

Also extend the existing `__init__.py` test (implicit, covered by
import-level checks) to confirm `read_network_interfaces` is
reachable.

#### Expected Quality Gates

Same as Parts 2–3.

#### Expected Coverage

- `cli/src/bcs/platform/adapters/network/adapter.py` — 100% statement
  and branch coverage.

#### Definition of Done

- [ ] `adapter.py` exists and is the only module importing
  `CommandRunner`/`bcs.platform.execution`.
- [ ] Locale env is a full `os.environ.copy()` (not a two-key dict) —
  verified by test assertion `"PATH" in call["env"]`.
- [ ] `check=False` always; `timeout_seconds` always explicit.
- [ ] Every adapter-side error path maps to the right typed exception.
- [ ] `__init__.py` re-exports `read_network_interfaces` in `__all__`.
- [ ] All quality gates pass.
- [ ] `CHANGELOG.md` entry.
- [ ] `docs/NETWORK_ADAPTER.md` status banner updated.
- [ ] The package's `__all__` is reviewed against every public name in
  `models.py`/`errors.py`/`parser.py`/`adapter.py` — nothing new is
  silently unreachable, nothing unintended is exposed.

---

### Part 5 — Host Discovery Typing and Composition-Root Wiring

#### Objective

Narrow the `HostDiscoveryAdapters`/`HostDiscoverySnapshot` network slot
from the current `Callable[[], list[NetworkInterface]]`/`tuple[NetworkInterface, ...]`
to the adapter's concrete return type, and wire
`read_network_interfaces` into the composition root in
`bcs.app.main()`.

#### Files to Modify

- `cli/src/bcs/inventory/discovery/models.py`:
  - `HostDiscoveryAdapters.network`: type changes from
    `Callable[[], list[NetworkInterface]] | None` to
    `Callable[[], NetworkInterfaceStatus] | None`.
  - `HostDiscoverySnapshot.network`: type changes from
    `tuple[NetworkInterface, ...]` to `NetworkInterfaceStatus | None`.
  - Remove the import of `bcs.inventory.models.NetworkInterface` if no
    longer needed. Add import of
    `bcs.platform.adapters.network.models.NetworkInterfaceStatus`.
  - Update module-level docstring that describes the slot.
- `cli/src/bcs/app.py`:
  - Add `from bcs.platform.adapters.network.adapter import read_network_interfaces`.
  - Replace `network=collectors.collect_network` with
    `network=functools.partial(read_network_interfaces, runner=command_runner)`.
  - Keep `collectors.collect_network` in the `collectors` import if
    still used elsewhere (it is, by `HostInventory`'s own network
    collection flow — do NOT remove that import).
- `cli/tests/test_host_discovery_pipeline.py`:
  - Import `NetworkInterfaceStatus` and `read_network_interfaces`.
  - Update `FakeCommandRunner` fixtures to handle `ip -json addr show`.
  - Add assertions that the wired `network` slot returns a
    `NetworkInterfaceStatus`.
  - Verify that `HostDiscoverySnapshot.network` is
    `NetworkInterfaceStatus | None` (not a tuple).
  - Verify that a `PlatformError` from the network slot isolates into
    `caveats` correctly.
  - Verify that the network slot is called in the correct order
    (`efi`, `storage`, `secure_boot`, `filesystem`, `network`, ...).
- `cli/tests/test_host_discovery_wiring.py` (or equivalent) — update to
  verify the composition root builds `network` as a
  `functools.partial(NetworkAdapter.read_network_interfaces, ...)`.

#### Files That Must NOT Be Modified

- `cli/src/bcs/platform/adapters/network/*.py` — all four files are
  already complete; no structural changes needed.
- `cli/src/bcs/inventory/discovery/orchestrator.py` — orchestrator is
  domain-agnostic; no changes needed.
- Any sibling adapter.
- `bcs.inventory.collectors` — the existing `collect_network()` stays
  for the Host Inventory's own schema until a separate ADR-0008
  amendment decides otherwise.

#### Tests to Add

| Test module | Verifies | Approach |
|---|---|---|
| `test_host_discovery_pipeline.py` (extend existing file) | The wired `network` slot is invoked by `discover()`; returns `NetworkInterfaceStatus` (not a tuple); a `PlatformError` from the slot produces a `caveats` entry. | `FakeCommandRunner` returning a synthetic `ip -json addr show` output for the success case; raising `PlatformError` for the failure case. |
| `test_host_discovery_wiring.py` (extend existing file) | The composition root constructs `network` as `functools.partial(read_network_interfaces, runner=<same CommandRunner as other slots>)`. | CLI-driven test patching `SubprocessCommandRunner`. |

#### Documentation to Update

- `docs/NETWORK_ADAPTER.md` — change status banner: "Network Adapter
  fully implemented." Update all "not yet implemented" markers to
  "[implemented]".
- `docs/IMPLEMENTATION_STATUS.md`:
  - § 2 Architecture Components — Network row: status → "✅ Fully
    implemented".
  - § 4 Platform Adapter Matrix — Network row: all columns → ✅ .
  - § 5 Host Discovery Status — Network moves from "wired (sysfs)" to
    "wired (tool-based adapter)".
  - § 8 Outstanding Work — remove the Network adapter medium item.
- `docs/HOST_DISCOVERY_ORCHESTRATOR.md` — update the
  `HostDiscoveryAdapters`/`HostDiscoverySnapshot` field tables and
  dependency diagram to show the network slot uses the tool-based
  adapter.
- `docs/PLATFORM_LAYER.md` — update the "How Future Adapters Use It"
  table to mark Network as implemented.
- `cli/src/bcs/platform/adapters/network/__init__.py` — update module
  docstring to remove "not yet implemented" language.
- `CHANGELOG.md` — `[Unreleased]` entry documenting Parts 2–5.

#### Expected Quality Gates

Same as all prior parts.

#### Expected Coverage

- `cli/src/bcs/inventory/discovery/models.py` — 100% (new paths from
  changed types).
- `cli/src/bcs/app.py` — covered by existing wiring tests.
- No new uncovered code in `cli/tests/test_host_discovery_pipeline.py`.

#### Definition of Done

- [ ] `HostDiscoveryAdapters.network` typed
  `Callable[[], NetworkInterfaceStatus] | None`.
- [ ] `HostDiscoverySnapshot.network` typed
  `NetworkInterfaceStatus | None`.
- [ ] `bcs.app.main()` binds `read_network_interfaces` via
  `functools.partial`, sharing the single `SubprocessCommandRunner`.
- [ ] All pipeline/wiring tests pass with the new concrete type.
- [ ] Mermaid diagrams in NETWORK_ADAPTER.md marked as implemented.
- [ ] All documentation status banners updated.
- [ ] `IMPLEMENTATION_STATUS.md` reflects full implementation.
- [ ] `CHANGELOG.md` entry.
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` — all green.

---

### Part 6 — Repository-Wide Consistency Pass

#### Objective

Synchronise every cross-reference, verify every link, update every
document that references the Network Adapter, and add CHANGELOG entries
for Parts 2–5.

#### Files to Modify (Verification, Not Structural Change)

- `CHANGELOG.md` — ensure `[Unreleased]` entries exist for Parts 2–5
  (or edit a single comprehensive entry). Format per existing precedent
  (see the Secure Boot Adapter's own four `CHANGELOG.md` entries for
  the expected level of detail):
  - What was added (models, parser, errors, adapter parts separately).
  - What tests were added (new test modules, total test count).
  - What remains out of scope.
- `docs/NETWORK_ADAPTER.md` — verify every internal anchor still
  resolves after any heading changes during implementation.
- `docs/README.md` — update the documentation-table row for the Network
  design document if the implementation-status phrase changed.
- `README.md` (root) — same.
- `AGENTS.md` — if the Project Orientation paragraph's list of
  implemented adapters needs updating to reflect the fifth completed
  adapter.
- `docs/ROADMAP.md` — update Phase 0 row if it tracks per-adapter
  completion.
- `cli/tests/fixtures/README.md` — add the `network/` category to the
  root corpus table, referencing the category README.
- `cli/src/bcs/platform/__init__.py` — verify its docstring lists
  `network` as implemented.
- `cli/src/bcs/inventory/discovery/__init__.py` — same.

#### Verification Checklist

- [ ] Every internal anchor (`#section-name`) in `NETWORK_ADAPTER.md`
  resolves correctly — use a Markdown-aware tool or manual scan.
- [ ] Every cross-document reference from `NETWORK_ADAPTER.md` to a
  sibling doc (e.g. `docs/EFI_ADAPTER.md#read-only-guarantee`) resolves.
- [ ] Every cross-document reference **to** `NETWORK_ADAPTER.md` from
  other docs resolves (grep for `NETWORK_ADAPTER.md` in `docs/`,
  `cli/src/bcs/`, and `README.md`).
- [ ] No document says "Proposed" or "not yet implemented" for a
  completed part.
- [ ] No ADR collision — verify no sibling document reserved
  `ADR-0012` for an unrelated decision (this plan does not add an ADR;
  it is purely an implementation of the existing pattern).
- [ ] `cli/tests/fixtures/network/README.md`'s inventory table is
  accurate.
- [ ] The test count documented in `IMPLEMENTATION_STATUS.md` is
  updated to reflect the new tests.

#### Files That Must NOT Be Modified

- Any code file outside the verification targets listed above.
- Any design decision or architecture document (`ARCHITECTURE.md`,
  `SPECIFICATION.md`, ADRs).

#### Definition of Done

- [ ] All internal and cross-document links verified.
- [ ] No stale "not yet implemented" claim exists for any completed
  part.
- [ ] `CHANGELOG.md` has a comprehensive `[Unreleased]` entry.
- [ ] `IMPLEMENTATION_STATUS.md` test count matches reality.
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` — all
  green (re-run after any documentation changes that touched `.py`
  files).
- [ ] Temporary files (scratch scripts, verification virtual
  environments) removed.

---

## 3. Implementation Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **`ip -json addr show` format changes** across `iproute2` versions on the target platform (Ubuntu 24.04 LTS). | Low | Parser may not produce correct `NetworkInterfaceStatus` for every real-machine output variant. | Permissive parser design (unrecognized fields silently ignored); six required fixture scenarios capture known variations; real capture from a LliureX system before moving beyond Part 3. |
| **`_UNAVAILABLE_PATTERNS` incomplete** — real `ip -json addr show` failure modes produce `stderr` text not covered by the patterns. | Medium | A non-zero exit that should map to `NetworkUnavailableError` instead falls through to the generic `NetworkError`. | Conservative start: include the most common patterns (`permission denied`, netlink socket errors). Add patterns as real machine observations surface them. The base `NetworkError` is always a safe fallback. |
| **Concurrent changes to `bcs.inventory.discovery.models`** or `bcs.app.main()` during Part 5 (composition-root wiring). | Medium | Merge conflicts with parallel work on other adapters or the CLI. | Part 5 depends only on Parts 2–4, which are architecture-agnostic library code; `models.py`/`app.py` changes are the only collision surface. Keep Part 5's scope narrow and coordinate against any concurrent Host Discovery work. |
| **`bcs.inventory.models.NetworkInterface` diverging** from the Platform Layer's `NetworkInterface` before Part 5 wiring completes. | Low | Type mismatch at the composition root. | The two models are deliberately independent per [NETWORK_ADAPTER.md § Naming Rationale](NETWORK_ADAPTER.md#naming-rationale); no code makes them interchangeable. Part 5 changes only the orchestrator's slot type, not the inventory model. A future ADR-0008 amendment will reconcile them separately. |
| **Test count inflation** across Parts 2–5 exceeds the ~100 new tests typical of a single-adapter full implementation (EFI: 79, Storage: 57, Secure Boot: ~50, Filesystem: ~80). | Medium | `CHANGELOG.md` entry may be inaccurate if counts are estimated rather than collected. | Run `pytest --collect-only` after each part's tests are written, before writing the `CHANGELOG.md` entry — exactly the precedent from [PATTERNS.md § 7](PATTERNS.md#7-common-mistakes). |

---

## 4. Likely Edge Cases

These are cases the parser and adapter must handle; they should all
be covered by synthetic test scenarios (not real-corpus placeholders,
per the established rule that malformed/edge-case fixtures are never
part of the captured-output corpus):

| Edge case | Layer | Expected behaviour |
|---|---|---|
| `ip -json addr show` returns an empty JSON array `[]` | Parser | Returns `NetworkInterfaceStatus(interfaces=())` — valid, not an error. |
| `ip -json addr show` returns valid JSON but not an array | Parser | `ValueError` ("expected a JSON array"). |
| An entry has no `ifname` field | Parser | `ValueError` quoting the 1-based entry index. |
| An entry has `ifname: ""` (empty string) | Parser | `ValueError` — same as missing. |
| `address` field absent from an entry | Parser | `mac_address = None` — permissive, not an error. |
| `address` field is `"00:00:00:00:00:00"` | Parser | `mac_address = None` — normalised to `None` per design. |
| `addr_info` absent from an entry | Parser | `ip_addresses = ()`. |
| `addr_info` is not an array (e.g. `null` or a string) | Parser | Treated as absent — `ip_addresses = ()`. |
| `addr_info` entry with `family` other than `inet`/`inet6` | Parser | Silently skipped for that entry. |
| `flags` field absent from an entry | Parser | Raises `ValueError` if `flags` is missing (required for `is_up`/`is_loopback` determination). |
| `flags` is present but neither `"UP"` nor `"LOWER_UP"` | Parser | `is_up = False`. |
| `ip` exits non-zero, `stderr` matches an unavailable pattern | Adapter | `NetworkUnavailableError`. |
| `ip` exits non-zero, `stderr` does not match any pattern | Adapter | `NetworkError(result=result)`. |
| `ip` not on `PATH` | Adapter | `CommandNotFoundError` (propagated unchanged). |
| Parser raises `ValueError` on zero-exit output | Adapter | `NetworkParseError(text=...)` chained from the original. |
| No interface has `"LOOPBACK"` flag (e.g. container without loopback) | Parser | No entry has `is_loopback=True`; all interfaces treated as non-loopback. |
| Two interfaces with the same name (kernel-internal aliasing, VLANs) | Parser | Both entries retained as-is; `NetworkInterfaceStatus` does not deduplicate. |
| `timeout_seconds=None` passed explicitly | Adapter | No timeout applied — delegates to `CommandRunner`'s own behaviour. |

---

## 5. Fixture Corpus Required

Six required scenarios for `cli/tests/fixtures/network/`, following the
convention established by every sibling adapter:

| Scenario | What it exercises | Real capture needed? |
|---|---|---|
| `ethernet-up` | One Ethernet interface UP with an IPv4 address — the baseline case. | Yes (real machine/VM) |
| `ethernet-down` | Interface present but administratively DOWN — exercises `is_up=False`. | Yes |
| `multi-interface` | Ethernet + loopback + WiFi, the common real-machine case — exercises multiple entries and loopback detection. | Yes |
| `ipv6-only` | Only IPv6 link-local addresses, no IPv4 — exercises the IPv6 parsing path without IPv4. | Yes |
| `no-address` | Interface present but no assigned addresses — exercises `ip_addresses=()`. | Yes |
| `empty` | Empty JSON array `[]` — not expected on a real machine but a valid parser input. | No (synthetic) |
| `unavailable-stderr` | `stderr` output for the non-UEFI/unavailable case (per the corpus's stderr-suffix convention). | Yes |

All six scenario files start as zero-byte placeholders (with `unknown`
for the tool version). Real captures must come from a LliureX machine
on Ubuntu 24.04 LTS — never fabricated. The `empty` scenario is
synthetic (a zero-byte placeholder with `""` as its content, valid
JSON for an empty array — or a one-byte file containing `[]`).

The fixture README must document:
- Exact capture command: `LC_ALL=C LANG=C ip -json addr show`
- Flat layout (no OEM subdirectories), matching `secureboot/`'s
  precedent.
- Naming convention: `ip_<version>_ubuntu-24.04_<scenario>.txt`
- Inventory table with all six scenarios and their placeholder status.

---

## 6. Recommended Order of Execution

| Step | Agent | Notes |
|---|---|---|
| 1. Part 2 (errors) | Any agent | No dependencies; self-contained. |
| 2. Part 3 (parser + fixtures) | Any agent | No dependency on Part 2. Can run concurrently with Step 1. |
| 3. Part 4 (adapter + `__init__.py`) | Same or different agent | Depends on Parts 2 and 3 both being complete. |
| 4. Part 5 (wiring) | Same agent as Step 3 recommended | Depends on Part 4; touches `bcs.app.main()` and `discovery/models.py` — coordination-critical files. |
| 5. Part 6 (consistency pass) | Any agent | Depends on all prior parts. Verifies everything; no code changes. |

Steps 1 and 2 are safe to parallelise across two agents. Steps 3–5
must be sequential to avoid merge conflicts.

---

## 7. Files Likely to Conflict During Parallel Development

| File | Risk during parallel work | Recommended guard |
|---|---|---|
| `cli/src/bcs/app.py` | Composition-root wiring (Part 5) touches the same `main()` function any other adapter's wiring step would touch. | Only one agent works on Part 5 at a time. Coordinate with any concurrent adapter-wiring work. |
| `cli/src/bcs/inventory/discovery/models.py` | Part 5 changes `HostDiscoveryAdapters.network` and `HostDiscoverySnapshot.network` types. Any concurrent change to the discovery models (e.g. adding a new slot for another adapter) will conflict. | Same as above. |
| `cli/tests/test_host_discovery_pipeline.py` | Part 5 extends this file; any concurrent adapter's wiring step also extends it. | Merge carefully; each adapter's test additions are additive (new `FakeCommandRunner` cases, new assertions). |
| `CHANGELOG.md` | Every part adds an entry. If multiple agents write entries concurrently, order and merge conflicts are inevitable. | Accumulate entries in a single pass (Part 6). Or assign a single agent to write the final `CHANGELOG.md` entry. |
| `docs/NETWORK_ADAPTER.md` status banner | Updated after each part. Concurrent updates to different sections are fine; concurrent updates to the same line (status banner) are not. | Each part should only change its own section's status markers. The banner update can wait until Part 6's consistency pass. |
| `docs/IMPLEMENTATION_STATUS.md` | Updated in Part 5. Any concurrent adapter reaching implementation will also touch this file. | Coordinate or merge carefully. |
