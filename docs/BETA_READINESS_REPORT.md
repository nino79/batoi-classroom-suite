# Beta Readiness Report — `bcs` CLI

**Date:** 2026-07-09
**Scope:** Final Beta readiness audit of `cli/` (the only implemented component; Boot Manager/Builder/Deploy remain Phases 1-3, planning-only — see [ROADMAP.md](../ROADMAP.md)).
**Audit type:** Verification pass across CLI behavior, packaging, installation, known limitations, TODO/FIXME markers, and CI coverage. Per the audit's own scope rule, defects were fixed only where they were genuine Beta blockers; everything else is documented below.

---

## Summary

One genuine Beta blocker was found and fixed: `bcs <command> --help` (and `-h`) showed the top-level help instead of the command's own help, for every implemented subcommand, directly contradicting `docs/CLI.md`'s own Global Options table. Everything else audited — the 4 other command surfaces, all 3 output modes, all 3 installation paths, packaging metadata, and the quality gates — passed without requiring code changes. Ten pre-existing, already-documented limitations remain valid or are noted below where their status has changed since M3/M4.

**Estimated Beta readiness: 80%.**
**Release recommendation: Do not tag Beta yet.** The codebase, packaging, and quality gates are ready; the remaining gap is exclusively M5 (physical/VM hardware validation), which by definition cannot be completed from this environment and has not been started per `docs/BETA_ROADMAP.md`.

---

## Blockers

### Fixed during this audit

| # | Defect | Severity | Status |
|---|---|---|---|
| 1 | `bcs <command> --help`/`-h` always showed the top-level help instead of the command's own — see [Root Cause](#root-cause-the-help-defect) below. | High (violates documented `CLI-002`/`CLI-003` behavior for every subcommand) | **Fixed** — `cli/src/bcs/argv_normalize.py`, `cli/tests/test_argv_normalize.py` |

### Remaining (not fixed — outside this audit's authority to resolve)

| # | Blocker | Why it blocks Beta |
|---|---|---|
| 2 | **No physical/VM hardware validation (M5).** `docs/BETA_ROADMAP.md` M5 is entirely unchecked: no environment in `HARDWARE_VALIDATION_MATRIX.md` has been validated since M3/M4 landed. All "M3/M4 complete" checkmarks in the roadmap are explicitly qualified "(code)" — real-hardware confirmation is a separate, unstarted milestone. | The Secure Boot, Storage, and Network Adapters have never been exercised against real UEFI firmware, real `mokutil`, or a real NVMe disk in this Beta cycle; every test to date is either a unit test against a `FakeCommandRunner` or was run on this Windows dev machine (which reports `unsupported`/empty for nearly every hardware fact, as seen throughout this audit). Shipping Beta without at least one confirmed run per `HARDWARE_VALIDATION_MATRIX.md` environment is the single largest known-unknown. |
| 3 | **M7 (release engineering) not done.** No Beta git tag exists; `CHANGELOG.md`'s `[Unreleased]` section has not been cut into a release section. | Procedural, but explicitly listed as a Beta Definition-of-Done item in `docs/BETA_ROADMAP.md`. |

Neither #2 nor #3 is a code defect this audit's "only implement genuine blockers" instruction authorizes fixing — #2 requires physical/VM access this environment doesn't have, and #3 is a release-process action, not a bug.

---

## Root Cause: the `--help` defect

`docs/CLI.md`'s Global Options table states unambiguously:

> `--help, -h` — Show help for **the current command**.
> `--version` — Shorthand for `bcs version` at the root only (`bcs --version`, **not valid after a subcommand**).

`cli/src/bcs/argv_normalize.py` implements a documented, deliberate preprocessing pass that hoists global options appearing *after* the subcommand to *before* it, so that `bcs -v build` and `bcs build -v` are equivalent (Typer/Click otherwise only recognizes a parent command's own options before the subcommand name). Its hoist table, `_GLOBAL_OPTIONS`, included `--help`, `-h`, and `--version` alongside genuine global runtime options like `-v`/`--output`. Because these three are eager Click options that also exist on the root command, hoisting them made `bcs doctor --help` get silently rewritten to `bcs --help doctor` before Typer ever parsed it — so every subcommand's `--help` showed the root command list instead of its own `--check`/`--strict`/argument documentation, and `bcs <subcommand> --version` silently printed the root version instead of erroring, contradicting the "not valid after a subcommand" contract.

Verified with a manual reproduction (`normalize_argv(['doctor', '--help'])` returned `['--help', 'doctor']`) before diagnosing root cause, and confirmed the bug reproduces identically on both the currently pinned Typer range's installed version (0.26.8) and an older one (0.15.4) — ruling out a Typer/Click version regression and confirming this project's own preprocessing was the cause.

**Fix:** removed `--help`, `-h`, `--version` from `_GLOBAL_OPTIONS` (they are not "equivalent before or after" options — `--help` is scoped to whichever command level it appears after, and `--version` is root-only, exactly as documented). Verified via:
- Direct `normalize_argv()` calls for all previously-broken cases, plus mixed cases like `bcs doctor -v --help` (confirms `-v` is still correctly hoisted while `--help` is not).
- Live CLI runs: `bcs doctor --help`, `bcs validate --help`, `bcs inventory -h`, `bcs version --help` now each show their own options; `bcs validate --version` now correctly errors `No such option: --version` instead of silently succeeding; `bcs --help`/`bcs --version` (no subcommand) are unaffected.
- 5 new parametrized regression tests added to `cli/tests/test_argv_normalize.py` (19 tests in that file now, up from 14; all pass).
- Full quality gates re-run after the fix: `ruff check` clean, `ruff format --check` clean, `mypy --strict` clean (62 files), `pytest` 1074 passed (up from 1069), coverage unchanged at 96%.
- Verified in all three installation forms (editable, built wheel, built sdist) into three separate clean virtual environments — see [Installation Verification](#installation-verification).

**Note (separate, not fixed):** `docs/CLI.md` also documents `bcs help build`/`bcs build help` (bare-word forms) as two of three equivalent ways to request help. Neither is implemented at all (confirmed: `bcs help doctor` → `unknown command 'help'`; `bcs doctor help` → `Got unexpected extra argument(s) (help)`). This is a pre-existing gap between documented and built behavior, not a regression — implementing it is a new feature (a `help` pseudo-command / positional dispatch), which this audit's "no new features unless a real defect" scope does not authorize. Documented here as a recommendation, not fixed.

---

## Command Verification

All 5 implemented commands (`--help`, `version`, `validate`, `inventory`, `doctor`) were exercised directly, both before and after the fix above.

| Command | `--help`/`-h` | Functional run | Notes |
|---|---|---|---|
| `bcs --help` (root) | ✅ | ✅ | Lists all 11 commands, unaffected by the fix (no subcommand to hoist past). |
| `bcs version` | ✅ (own help, post-fix) | ✅ | `commit`/`buildDate` are `null` in this dev checkout by design — populated via `BCS_BUILD_COMMIT`/`BCS_BUILD_DATE` env vars at release-build time, not set here. |
| `bcs validate` | ✅ (own help, post-fix) | ✅ | Verified against `config/examples/default.yaml` (valid), a nonexistent path (exit 3, correct error), and `--strict`. |
| `bcs inventory` | ✅ (own help, post-fix) | ✅ | Reports `unsupported`/empty fields on this non-Linux Windows dev box — expected, matches this session's prior VM-validation findings; not a regression. |
| `bcs doctor` | ✅ (own help, post-fix) | ✅ | 4 fail / 1 warn / 4 skip on this dev box — expected for the same reason; exit code 4 correctly reflects failing checks. |
| 7 stub commands (`build`, `install`, `deploy`, `backup`, `restore`, `update`, `config`) | ✅ (own help, post-fix) | ✅ | Each exits 1 with a clear "not implemented, owned by X" message, per design. |
| Unknown command | — | ✅ | `bcs docter` → `unknown command 'docter' - did you mean 'doctor'?`, exit 8. |

All three output modes (`text`, `json`, `yaml`) were exercised for `version`, `inventory`, `validate`, and `doctor`. All produced well-formed, schema-consistent output in every mode; no mode-specific defects found.

---

## Installation Verification

Built with `python -m build` (hatchling backend) from `cli/`; both artifacts built cleanly with no warnings.

| Artifact | Contents check | Install target | Result |
|---|---|---|---|
| Wheel (`bcs-0.1.0-py3-none-any.whl`) | Contains exactly the `bcs` package tree (no stray `.pyc`, no `__pycache__`); `entry_points.txt` correctly maps `bcs = bcs.__main__:main`; `METADATA` correctly lists all 4 runtime dependencies with their pinned ranges and the `dev` extra. | Clean venv | ✅ `bcs --version`, `bcs doctor --help` (post-fix) both correct. |
| Sdist (`bcs-0.1.0.tar.gz`) | Includes `src/bcs/**`, `tests/**` (incl. fixtures), `README.md`, `pyproject.toml`, `PKG-INFO`, `.gitignore` — standard hatchling default inclusion, no unexpected files. | Clean venv | ✅ `bcs --version`, `bcs inventory --output json` both correct. |
| Editable install (`pip install -e .`) | — | Clean venv | ✅ `bcs --version`, `bcs validate --help` (post-fix) both correct. |

All build/install artifacts were created and installed under the session scratchpad, outside the repository, and were not committed — consistent with the "no build artifacts or binaries" repository rule.

## Packaging Review

- **`pyproject.toml`**: `[build-system]` uses `hatchling`; `[project]` declares name/version/description/readme/license/classifiers/dependencies correctly; `[project.scripts]` correctly registers the `bcs` entry point; `[tool.hatch.build.targets.wheel] packages = ["src/bcs"]` is correct and matches the wheel's actual contents.
- **Entry points**: verified directly in the built wheel's `entry_points.txt` — correct.
- **Version metadata**: `bcs.__init__`/`pyproject.toml` both agree on `0.1.0`; `bcs --version` and `bcs version --output json` both report it consistently.
- **MANIFEST**: no `MANIFEST.in` exists, which is correct — hatchling doesn't use the setuptools MANIFEST mechanism; sdist inclusion is handled by its own defaults, verified above to be sane.
- **`py.typed` marker**: absent. Minor — `bcs` is mypy-strict internally and PEP 561 recommends shipping `py.typed` for typed packages, but `bcs` is consumed as an end-user CLI, not imported as a library, so this has no practical impact. Recommendation only, not a blocker.
- **`LICENSE` file**: not present inside `cli/` (it exists at the repo root and is correctly referenced via `license = { text = "MIT" }` in `pyproject.toml`, which is a complete, valid SPDX-style declaration on its own). Cosmetic only.

---

## Known Limitations — Validity After M2/M3/M4

Reviewed all 10 entries in `docs/KNOWN_LIMITATIONS.md` against the current codebase (not modified — flagged here per the audit's "document, don't implement" default, and because this doc is being actively maintained by a concurrent session's documentation/tooling work):

| Limitation | Still valid? |
|---|---|
| `esp`/`usb-storage` checks have no adapter equivalent | ✅ Still valid — confirmed unchanged. |
| 7 stub commands | ✅ Still valid, by design. |
| Host Inventory schema excludes full discovery-domain facts | ✅ Still valid — confirmed unchanged. |
| Fixture corpora are placeholders | ✅ Still valid — spot-checked; all fixture `.txt` files under `cli/tests/fixtures/{firmware,network,secureboot,storage}/` are still 0 bytes. |
| Missing `FakeCommandRunner` test double | ❌ **Stale — now resolved.** `cli/tests/fake_command_runner.py` exists (162 lines) and is imported by all 5 adapter test modules plus `test_host_discovery_pipeline.py`. This entry should be removed or marked resolved by whichever session owns `KNOWN_LIMITATIONS.md` next. |
| Ruff `S603`/`S607` scoping not narrowed | ✅ Still valid — `cli/pyproject.toml` still disables both globally. |
| No CPU/Memory/TPM tool-based adapters | ✅ Still valid. |
| No TPM adapter exists | ✅ Still valid. |
| `FrozenModel`/`FrozenExtensibleModel` not relocated | ⚠️ **Partially stale.** The entry's own description no longer matches the code: `bcs.config.models` does not define classes named `FrozenModel`/`FrozenExtensibleModel` at all — it has `StrictModel`/`ExtensibleModel`, which are similar in spirit (forbid-extra vs. allow-`x-`-prefixed-extra) but, unlike `bcs.inventory.models.FrozenModel`, are **not** actually frozen (`ConfigDict` has no `frozen=True`). Both do already share the one genuinely duplicated piece of logic (`bcs.model_utils.reject_non_x_extra`). Still Low severity/cosmetic, but the limitation's own wording should be corrected next time it's touched. |
| `CLI.md` references stale implementation status | ✅ Still valid — `docs/CLI.md` line 98 still says ADR-0009 is "(Accepted, not yet implemented)" even though the Platform Layer it describes is fully implemented. |

No entry was found to be a Beta blocker; the one "stale" entry (`FakeCommandRunner`) undersells current progress rather than hiding a problem, and the other ("FrozenModel") is a wording inaccuracy, not a functional gap.

## TODO/FIXME/XXX Review

`grep`-searched `cli/src/` and `cli/tests/` for `TODO`, `FIXME`, `XXX`: **zero matches in either.** Nothing to triage for Beta-blocking status.

## CI Review

`.github/workflows/ci.yml` runs 4 jobs gated behind `all-green`: `lint` (ruff check + format), `typecheck` (mypy), `test` (pytest on 3.12 and 3.13), and `cli-smoke-test` (installs the package for real and runs `bcs --help`, `bcs version --output json`, `bcs inventory --output json`, `bcs doctor --output json` non-gated, `bcs validate ... --output json`).

**Gap found:** the smoke-test job never runs `bcs <subcommand> --help`, only the bare top-level `bcs --help`. This is precisely why the `--help` defect fixed in this audit shipped undetected — no CI path exercised it. The regression test added to `test_argv_normalize.py` now covers the actual root cause at the unit level (faster and more precise than a subprocess-level CI assertion would be), but a CI-level assertion would still catch a *future* regression introduced anywhere else in the help-rendering pipeline (e.g. in Typer/Click configuration itself, which the unit test can't see). **Recommendation, not implemented in this pass** (CI/tooling changes are explicitly the concurrent session's area per this session's own working agreement, and the unit-level fix is the correct minimal fix for the defect found): add a `bcs doctor --help` (or similar) assertion to `cli-smoke-test`.

Other minor CI observations (all recommendations, none blocking):
- No smoke-test step exercises `--output yaml`, only `text` (implicit) and `json`.
- No smoke-test step exercises a non-zero exit path (e.g. `bcs validate` against a missing file) to confirm exit codes survive a real install.
- Stub commands are never smoke-tested.

---

## Quality Gates (final state, after the fix)

| Gate | Result |
|---|---|
| `ruff check` | ✅ All checks passed |
| `ruff format --check` | ✅ 119 files already formatted |
| `mypy` (strict) | ✅ Success: no issues found in 62 source files |
| `pytest` | ✅ 1074 passed |
| Coverage | 96% (unchanged from before this audit) |

---

## Recommendations (non-blocking)

1. Implement the `bcs help <command>` / `bcs <command> help` forms `docs/CLI.md` documents, or narrow the doc to match what's actually built (`--help`/`-h` only).
2. Add a `py.typed` marker if `bcs` internals are ever expected to be imported by another package.
3. Correct `docs/KNOWN_LIMITATIONS.md`'s `FakeCommandRunner` entry (resolved) and the `FrozenModel`/`FrozenExtensibleModel` entry's description (class names/behavior have drifted from what it describes).
4. Fix `docs/CLI.md` line 98's stale "(Accepted, not yet implemented)" ADR-0009 annotation.
5. Extend `cli-smoke-test` in CI with a subcommand `--help` assertion, a `--output yaml` run, and a non-zero-exit-path assertion.

## Release Recommendation

**Do not tag Beta yet.** Code, packaging, and quality gates are in a releasable state today — the fix in this audit removes the one genuine functional blocker found. The remaining path to Beta is entirely M5 (physical/VM hardware validation per `docs/BETA_ROADMAP.md` and `docs/HARDWARE_VALIDATION_MATRIX.md`) and M7 (release tag/changelog cut), neither of which this audit is positioned to complete. Recommend: run the `BETA_RELEASE_CHECKLIST.md` against at least the E01 VirtualBox environment and one physical UEFI/NVMe environment, log results in `VM_TEST_LOG.md`, then re-run this audit's quality-gate section on the exact commit intended for tagging before cutting `v0.2.0-beta.1`.
