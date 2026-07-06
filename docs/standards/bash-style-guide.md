# Bash Style Guide

Bash is BCS's primary implementation language (see [ADR-0004](../decisions/0004-bash-as-primary-implementation-language.md)). This guide is based on the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html), narrowed and adapted to BCS's specific target environment (Bash guaranteed, not POSIX `sh`; classroom-scale, unattended, single-technician-operated).

No implementation exists yet — this guide is written ahead of code so the first script written meets the same bar as the thousandth.

## Shell and Shebang

- Target shell is **Bash**, not POSIX `sh` — the target platform guarantees Bash (`PLAT-001`/`PLAT-002`), so Bash-only features (arrays, `[[ ]]`, `local`, `readonly`) are allowed and preferred over POSIX-portable workarounds.
- Every executable script starts with `#!/usr/bin/env bash`.
- Every script starts (immediately after the shebang) with:

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```

`set -euo pipefail` is non-negotiable for anything beyond a trivial one-liner: `-e` stops on unhandled errors, `-u` catches unset-variable typos, `-o pipefail` surfaces failures inside pipelines instead of only reporting the last command's status. This directly supports the "fail loudly during build/deploy" principle in [coding-standards.md](coding-standards.md#error-handling).

## Structure

A non-trivial script should be organized as:

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# 1. Constants / configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Function definitions
log_info() {
  printf '[INFO] %s\n' "$*" >&2
}

main() {
  # 3. Entry point — orchestration only, delegate to functions above
  ...
}

# 4. Invocation guard, so the file can also be sourced for testing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
```

The invocation guard matters for testability (`coding-standards.md`'s testing expectations) — it lets `bats` source the script and call individual functions without running `main`.

## Naming

See [naming-conventions.md](naming-conventions.md#bash) for the authoritative rules; summarized here:

- Functions and local variables: `lower_snake_case`.
- Constants and exported/environment variables: `UPPER_SNAKE_CASE`, declared `readonly` where possible.
- Private/internal functions not part of a script's external contract: prefix with `_` (e.g., `_validate_recipe_schema`).

## Quoting and Expansion

- Quote every variable expansion unless word-splitting is deliberately intended: `"${var}"`, not `$var`.
- Prefer `"${array[@]}"` over `"${array[*]}"` when iterating.
- Use `$(...)` command substitution, never backticks.
- Use `[[ ... ]]` for conditionals, never `[ ... ]` or `test`.
- Prefer parameter expansion (`${var:-default}`, `${var%.suffix}`) over calling out to `sed`/`awk`/`cut` for simple string manipulation.

## Error Handling

- Check the exit status of anything that can fail and is not already covered by `set -e` semantics (e.g., inside a conditional or a pipeline where you deliberately want to inspect the failure).
- Use a `trap` for cleanup (temp files, mounts) rather than relying on the script reaching its natural end:

```bash
readonly TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
```

- Exit codes are meaningful, not just `0`/`1`: document any non-zero exit code a script can return in a header comment, since Deploy's session reporting (`DEP-005`) and Boot Manager's fallback (`BM-005`) depend on distinguishing failure modes.

## Things to Avoid

- Parsing the output of `ls` — use globs or `find -print0` with `while read -r -d ''`.
- Useless use of `cat` (`cat file | grep x` → `grep x file`).
- Bashisms-on-top-of-bashisms that reduce readability for no benefit (e.g., obscure parameter-expansion golf) — clarity for the next maintainer outweighs cleverness, especially on a 10-year horizon.
- Global mutable state accessed deep inside unrelated functions — pass values as arguments where feasible.
- Silently discarding stderr (`2>/dev/null`) outside of a narrowly justified, commented case.

## Tooling

Once implementation begins, CI is expected to enforce:

- **[ShellCheck](https://www.shellcheck.net/)** — zero warnings, or an inline `# shellcheck disable=SCxxxx` with a comment explaining why.
- **[shfmt](https://github.com/mvdan/sh)** — consistent formatting (indentation, spacing), run with `-i 2 -ci` (2-space indent, indented case statements) to match this guide.
- **[bats](https://github.com/bats-core/bats-core)** — unit tests for functions, using the invocation-guard pattern above to source scripts without executing `main`.

Until this tooling is wired into CI, contributors are expected to run ShellCheck locally before opening a pull request that adds or modifies a script.
