# Test Fixture Corpus — Captured Tool Output

This directory holds **verbatim, captured output of real system-inspection
tools**, used to test Platform Layer adapter parsers
([docs/PLATFORM_LAYER.md § Testing Strategy](../../../docs/PLATFORM_LAYER.md#testing-strategy))
without touching a real OS or device. It is organized by **domain**, not by
tool, per the project's domain-driven naming rule
([docs/standards/naming-conventions.md § Domain-Driven Naming](../../../docs/standards/naming-conventions.md#domain-driven-naming)):

| Directory | Domain | Consuming adapter |
|---|---|---|
| [`firmware/`](firmware/README.md) | UEFI firmware boot configuration | `bcs.platform.adapters.efi` ([docs/EFI_ADAPTER.md](../../../docs/EFI_ADAPTER.md)) — fully implemented |
| [`storage/`](storage/README.md) | Block devices / partitions | `bcs.platform.adapters.storage` ([docs/STORAGE_ADAPTER.md](../../../docs/STORAGE_ADAPTER.md)) — fully implemented |
| [`secureboot/`](secureboot/README.md) | Secure Boot state | `bcs.platform.adapters.secureboot` ([docs/SECURE_BOOT_ADAPTER.md](../../../docs/SECURE_BOOT_ADAPTER.md)) — fully implemented |
| [`filesystem/`](filesystem/README.md) | Filesystems / mounts | `bcs.platform.adapters.filesystem` ([docs/FILESYSTEM_ADAPTER.md](../../../docs/FILESYSTEM_ADAPTER.md)) — fully implemented |
| [`network/`](network/README.md) | Network interfaces | `bcs.platform.adapters.network` ([docs/NETWORK_ADAPTER.md](../../../docs/NETWORK_ADAPTER.md)) — domain models, error hierarchy, and parser implemented; adapter pending |

Load fixtures in tests through the shared helpers in
[`../fixture_utils.py`](../fixture_utils.py) — never with ad hoc `open()`
calls — so placeholder handling and corpus conventions stay uniform across
every adapter's tests:

```python
from fixture_utils import iter_fixtures, load_fixture

text = load_fixture("firmware", "generic", "efibootmgr_18_ubuntu-24.04_single-boot.txt")
for path in iter_fixtures("firmware"):  # skips placeholders automatically
    ...
```

## How Fixtures Are Collected

1. Run the **exact command line the adapter's design specifies** — no extra
   flags, no post-processing — on a real machine or VM of the target platform
   (LliureX 23 / Ubuntu 24.04, `PLAT-001`/`PLAT-002`), redirecting **stdout**
   to the fixture file. The category README states the exact command.
2. The command MUST be run with the **`C` locale forced**, exactly as the
   Platform Layer's adapters will run it
   ([docs/PLATFORM_LAYER.md § Locale Policy](../../../docs/PLATFORM_LAYER.md#locale-policy)):

   ```
   LC_ALL=C LANG=C <command> > <fixture-name>.txt
   ```

   A fixture captured under any other locale is invalid: it does not
   represent what an adapter will actually see.
3. Record the capture's provenance (tool version, machine/VM model, OS,
   capture date, whether anonymization was applied) in the **inventory
   table of the category's README** — never inside the fixture file itself.
   Fixture files are verbatim tool output and contain **no comments, no
   headers, no annotations of any kind**.
4. If a scenario needs the tool's **stderr** or a non-zero exit code (e.g.
   error-mapping tests), capture stderr to its own fixture with an
   `-stderr` suffix in the scenario field, and record the exit code in the
   inventory table.

## Anonymization Rules

Captured output from real machines may embed identifying data. Before
committing a fixture:

- **Substitute in place; never restructure.** Never delete lines, columns, or
  whitespace, and never reorder anything — parsers must see byte-identical
  *structure* to real output. Only replace characters within a value.
- **Format-preserving replacements only.** Replace GUIDs/UUIDs (e.g. GPT
  partition GUIDs inside UEFI device paths), serial numbers, service/asset
  tags, and MAC addresses with synthetic values of **identical length and
  character class** (hex digits for hex digits, etc.).
- **Internally consistent.** If the same GUID appears three times in one
  capture, replace all three occurrences with the *same* synthetic GUID —
  cross-references within one fixture must survive.
- **Hostnames/usernames/network names** become generic equivalents.
- Product labels that identify only a product, not a person or site
  (`ubuntu`, `Windows Boot Manager`, an OEM model name), stay as-is.
- Mark `anonymized: yes` in the inventory table entry.

## Naming Convention

```
<tool>_<tool-version>_<platform>_<scenario>.txt
```

- Exactly four fields, separated by `_`; kebab-case (lowercase, `-`, `.`)
  within a field. Examples:
  `efibootmgr_18_ubuntu-24.04_dual-boot-windows.txt`,
  `efibootmgr_18_lliurex-23_boot-next-set.txt`.
- The `<tool-version>` field is the version the tool itself reports
  (e.g. `efibootmgr -V`); the `<platform>` field is the OS the capture was
  taken on.
- `unknown` is permitted in a field **only** for placeholder files (below);
  a real capture must record real values, renaming the placeholder.

## Placeholders

A **zero-byte `.txt` file** is a placeholder: a scenario the corpus needs
but for which no real output has been captured yet. Placeholders exist so
the required scenarios are visible and tracked in git, without inventing
fake tool output — **fabricated fixture content is never acceptable**, since
the entire value of this corpus is fidelity to real-world output. The
shared helpers treat zero-byte files accordingly: `iter_fixtures()` skips
them by default, and `load_fixture()` refuses to load one. Replacing a
placeholder means: capture per the rules above, rename with real
field values, and fill in the inventory table row.
