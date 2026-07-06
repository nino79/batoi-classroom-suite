# Standards

This directory documents the conventions BCS contributors are expected to follow. Standards exist so that a repository maintained over many years — likely by people who weren't present for its early decisions — stays consistent and predictable, rather than drifting toward whatever each contributor personally prefers.

## Contents

| Document | Covers |
|---|---|
| [coding-standards.md](coding-standards.md) | Cross-language principles: error handling, idempotency, logging, testing expectations. |
| [bash-style-guide.md](bash-style-guide.md) | Bash-specific conventions, since Bash is BCS's primary implementation language ([ADR-0004](../decisions/0004-bash-as-primary-implementation-language.md)). |
| [markdown-style-guide.md](markdown-style-guide.md) | How this documentation set itself is written and formatted, including Mermaid diagram conventions. |
| [naming-conventions.md](naming-conventions.md) | Naming rules spanning files, branches, commits, ADRs, requirement IDs, labels, and code identifiers. |

## Precedence

Where a language-specific guide (e.g., `bash-style-guide.md`) and the cross-language `coding-standards.md` appear to overlap, the language-specific guide wins for concrete syntax rules; `coding-standards.md` governs principles that apply regardless of language (error handling philosophy, idempotency, logging intent).

## Enforcement

These standards are currently enforced by code review (see [docs/processes/development-workflow.md](../processes/development-workflow.md)). As components reach implementation, automated enforcement (ShellCheck, `shfmt`, `markdownlint`) is expected to be added to CI — see the tooling notes in [bash-style-guide.md](bash-style-guide.md#tooling) and [markdown-style-guide.md](markdown-style-guide.md#tooling).
