# AGENTS.md

This file gives AI coding agents (Claude Code, GitHub Copilot Workspace, and similar tools) the working context and constraints they need to contribute usefully to Batoi Classroom Suite (BCS), without re-deriving it from scratch each session. Human contributors should read [CONTRIBUTING.md](CONTRIBUTING.md) instead; this file is agent-oriented and assumes familiarity with that document.

## Project Orientation

- **What this is:** an enterprise-grade deployment platform for LliureX classrooms, made of three components — Boot Manager, Builder, Deploy. See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design and [SPECIFICATION.md](SPECIFICATION.md) for requirements (referenced by ID, e.g. `BM-004`).
- **Current phase:** documentation and architecture only (see [ROADMAP.md](ROADMAP.md), Phase 0). There is no implementation code in this repository yet. Do not assume otherwise from folder names — `boot-manager/`, `builder/`, and `deploy/` currently contain only planning documentation.
- **Target platform is fixed and specific:** LliureX 23 on Ubuntu 24.04 LTS, UEFI firmware only, NVMe storage, Clonezilla as the deployment engine. Do not generalize designs to "any Linux" or "any firmware" — that genericity is explicitly out of scope (see [SPECIFICATION.md §4](SPECIFICATION.md#4-explicit-non-goals)).

## Hard Constraints

These reflect explicit decisions from the project maintainers. Do not work around them without first raising the conflict with the user.

1. **Do not implement installer logic or write Bash/shell scripts as part of documentation work.** This repository's current mandate is architecture and documentation, not implementation. If a task seems to require actual installer/build/deploy code, stop and confirm scope with the user rather than writing it.
2. **English only.** All files, code comments, identifiers, and commit messages are in English, regardless of the bilingual (Valencian/Spanish) end-user audience described in the specification.
3. **Keep the three components decoupled.** Never introduce a direct dependency of one component's internals on another's — only on the documented interfaces in [ARCHITECTURE.md §4](ARCHITECTURE.md#4-component-boundaries). If a change seems to require tighter coupling, that's a signal to write an ADR, not to just do it.
4. **Don't commit build artifacts or binaries.** No ISOs, disk images, compiled binaries, or generated fonts/icons beyond what's already tracked in `assets/`.
5. **Normative documents change carefully.** Edits to `ARCHITECTURE.md`, `SPECIFICATION.md`, or any file under `docs/specifications/` that change scope, requirements, or interfaces should be accompanied by an ADR under `docs/decisions/` (see [docs/decisions/README.md](docs/decisions/README.md)) and, once released, an update to [CHANGELOG.md](CHANGELOG.md).

## Repository Map

```
README.md, ARCHITECTURE.md, SPECIFICATION.md, ROADMAP.md   → normative top-level docs, read these first
CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md            → process/governance docs
CLAUDE.md                                                   → Claude Code-specific notes (imports this file)
CHANGELOG.md                                                → Keep a Changelog format, update under [Unreleased]
docs/architecture/*.md                                      → per-component architecture deep-dives, Mermaid diagrams
docs/specifications/*.md                                    → per-component requirements, expands SPECIFICATION.md
docs/decisions/*.md                                         → ADRs (Michael Nygard / MADR style)
docs/standards/*.md                                          → coding, Bash, Markdown, naming conventions
docs/processes/*.md                                          → development workflow, release process
docs/guides/*.md                                             → contributor-facing guides (getting started, FAQ)
docs/glossary.md                                             → domain terminology (LliureX, UEFI, ESP, etc.)
docs/repository-organization.md                              → canonical explanation of this map
boot-manager/, builder/, deploy/                             → one README.md each; planning docs only for now
assets/                                                       → shared branding assets (logos, icons, fonts, backgrounds)
.github/                                                      → issue templates, PR template, LABELS.md, DISCUSSIONS.md
```

## Conventions

Full detail lives in [docs/standards/](docs/standards/); summarized here so you don't need to fetch it for small edits:

- **Markdown style:** [docs/standards/markdown-style-guide.md](docs/standards/markdown-style-guide.md) — ATX headings (`#`), tables for structured requirements/matrices, [Mermaid](https://mermaid.js.org/) fenced code blocks for diagrams (used throughout `docs/architecture/`).
- **Requirement IDs:** `PLAT-xxx` (platform), `BM-xxx` (Boot Manager), `BLD-xxx` (Builder), `DEP-xxx` (Deploy), `NFR-xxx` (non-functional). Reuse existing prefixes; don't invent new ones without updating `SPECIFICATION.md`'s structure. Full rules in [docs/standards/naming-conventions.md](docs/standards/naming-conventions.md).
- **Commit messages:** [Conventional Commits](https://www.conventionalcommits.org/) (`docs:`, `feat:`, `fix:`, `chore:`, `adr:`), per [CONTRIBUTING.md](CONTRIBUTING.md).
- **Bash (once implementation begins):** Bash is the primary implementation language ([ADR-0004](docs/decisions/0004-bash-as-primary-implementation-language.md)); follow [docs/standards/bash-style-guide.md](docs/standards/bash-style-guide.md) (`set -euo pipefail`, ShellCheck-clean, `lower_snake_case` functions/locals, `UPPER_SNAKE_CASE` constants) — do not write Bash yet per Hard Constraint 1 above unless the user has confirmed the project is past Phase 0.
- **Cross-referencing:** link between documents with relative Markdown links rather than duplicating content. If the same fact needs to live in two places, prefer linking from the more detailed doc back to the normative one.

## When Asked to "Implement" Something

Given the current phase, if a request sounds like it wants working code (an actual boot menu, an actual image-build script, an actual Clonezilla invocation), treat that as out of scope for this phase and say so, pointing to [ROADMAP.md](ROADMAP.md) — unless the user has explicitly indicated the project has moved past Phase 0. When in doubt, ask rather than assume.

## Where to Look Before Proposing a Design Change

1. [ARCHITECTURE.md](ARCHITECTURE.md) and the relevant `docs/architecture/*.md` — is this already decided?
2. [docs/decisions/](docs/decisions/) — was this already considered and rejected in an ADR?
3. [SPECIFICATION.md](SPECIFICATION.md) and the relevant `docs/specifications/*.md` — does a requirement already constrain this?

If none of these cover it, propose a new ADR rather than silently changing behavior described elsewhere.
