# AGENTS.md

This file gives AI coding agents (Claude Code, Codex, MiniMax, and similar tools) the working context and constraints they need to contribute usefully to Batoi Classroom Suite (BCS), without re-deriving it from scratch each session. Human contributors should read [CONTRIBUTING.md](CONTRIBUTING.md) instead; this file is agent-oriented and assumes familiarity with that document.

## Project Orientation

- **What this is:** an enterprise-grade deployment platform for LliureX classrooms, made of three components — Boot Manager, Builder, Deploy. See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design and [SPECIFICATION.md](SPECIFICATION.md) for requirements (referenced by ID, e.g. `BM-004`).
- **Current phase:** the project is in **Phase 0 — Foundation** ([ROADMAP.md](ROADMAP.md)): architecture, specification, and core infrastructure. Boot Manager, Builder, and Deploy are Phases 1, 2, and 3 respectively — all three are `⏳ Planned`, meaning **none has started**. Do not assume otherwise from folder names — `boot-manager/`, `builder/`, and `deploy/` currently contain only planning documentation. Two things are real, implemented Phase 0 work: the `bcs` CLI framework (`cli/`, Python — [ADR-0007](docs/decisions/0007-python-for-the-bcs-cli.md)), with `build`/`install`/`deploy`/`backup`/`restore`/`update`/`config` still unimplemented stubs; and the **Platform Layer / Host Discovery** subsystem it hosts (`cli/src/bcs/platform/`, `cli/src/bcs/inventory/`) — `CommandRunner`, Host Inventory, and read-only hardware-discovery adapters (EFI implemented; Storage, Secure Boot, and a coordinating orchestrator designed or in progress — see `docs/PLATFORM_LAYER.md`, `docs/HOST_INVENTORY.md`, and the adapter-specific `docs/*_ADAPTER.md` documents). See [§ Workflow](#workflow) for what this implies about implementing anything else.
- **Target platform is fixed and specific:** LliureX 23 on Ubuntu 24.04 LTS, UEFI firmware only, NVMe storage, Clonezilla as the deployment engine. Do not generalize designs to "any Linux" or "any firmware" — that genericity is explicitly out of scope (see [SPECIFICATION.md §4](SPECIFICATION.md#4-explicit-non-goals)).

## Tool Precedence

`AGENTS.md` is the authoritative source for project-wide rules — workflow, scope, and conventions — regardless of which AI coding agent is operating. Tool-specific files (`CLAUDE.md`, and any future equivalent for another tool) may add operational detail specific to that tool's own features, but must never restate or contradict a rule that belongs here. If a tool-specific file and this file disagree, this file wins; treat the disagreement as a documentation bug to fix, not a choice to make silently.

## Hard Constraints

These reflect explicit decisions from the project maintainers. Do not work around them without first raising the conflict with the user.

1. **Do not implement Boot Manager, Builder, or Deploy logic.** Those three remain documentation and architecture only (Phases 1–3, all `⏳ Planned` — see [Project Orientation](#project-orientation)). If a request sounds like it wants working code for any of them — an actual boot menu, an actual image-build script, an actual Clonezilla invocation — treat that as out of scope and say so, pointing to [ROADMAP.md](ROADMAP.md), unless the user explicitly names that component's phase as begun (a general "go ahead" is not enough; look for an actual reference to the phase or its ROADMAP.md status). This does not extend to `cli/` — the `bcs` CLI framework and the Platform Layer/Host Discovery subsystem it hosts are legitimately implemented/in-progress Python work and are in scope today; see [cli/README.md](cli/README.md). When in doubt about anything else, ask rather than assume.
2. **English only.** All files, code comments, identifiers, and commit messages are in English, regardless of the bilingual (Valencian/Spanish) end-user audience described in the specification.
3. **Keep the three components decoupled.** Never introduce a direct dependency of one component's internals on another's — only on the documented interfaces in [ARCHITECTURE.md §4](ARCHITECTURE.md#4-component-boundaries). If a change seems to require tighter coupling, that's a signal to write an ADR, not to just do it.
4. **Don't commit build artifacts or binaries.** No ISOs, disk images, compiled binaries, or generated fonts/icons beyond what's already tracked in `assets/`.
5. **Normative documents change carefully.** Edits to `ARCHITECTURE.md`, `SPECIFICATION.md`, or any file under `docs/specifications/` that change scope, requirements, or interfaces need an ADR first — see [§ ADR Workflow](#adr-workflow).

## Workflow

- **Design first, implementation later.** A new Platform Layer component, adapter, orchestrator, or other architectural piece gets a design document under `docs/` (and, where [§ ADR Workflow](#adr-workflow) requires one, an accepted ADR) before any code — see `docs/EFI_ADAPTER.md`, `docs/STORAGE_ADAPTER.md`, and `docs/HOST_DISCOVERY_ORCHESTRATOR.md` for the pattern. A component is not implementable until: its design document exists, any ADR its design required has reached `Accepted`, and the user has explicitly approved implementation — approving the design is not the same as approving implementation.
- **Respect stated scope exactly.** When a request limits scope ("Part 1," "models only," "parser only," and similar), implement only that — never a later part, even if it looks like the obvious next step. Prefer stopping at a clean architectural boundary (a finished module, a finished layer) over partially starting the next one.
- **Don't expand scope because adjacent work already exists.** A sibling component being implemented, or a related field being an obvious addition, is not authorization to add it — that's a new request, not an implied one.

## Definition of Done

A `cli/` task is not complete until, whichever of the following apply to the change:

- Implementation matches the accepted design, or the explicitly scoped part of it (see [§ Workflow](#workflow)).
- `ruff check` and `ruff format --check` pass.
- `mypy` passes.
- `pytest` passes.
- Documentation that described the change as planned/proposed is updated to reflect it.
- `CHANGELOG.md` has an entry under `[Unreleased]`.
- Public exports (`__init__.py`, `__all__`) are reviewed — nothing new is silently unreachable, nothing unintended is exposed.
- Temporary files (scratch scripts, verification virtual environments) are removed.
- Internal links and heading anchors are verified — see [§ Documentation Workflow](#documentation-workflow).
- If a new ADR was created, [docs/decisions/README.md](docs/decisions/README.md)'s index is updated — see [§ ADR Workflow](#adr-workflow).

## ADR Workflow

Before proposing a change, check whether it's already decided: [ARCHITECTURE.md](ARCHITECTURE.md)/`docs/architecture/*.md`, [docs/decisions/](docs/decisions/) (was this considered and rejected already?), and [SPECIFICATION.md](SPECIFICATION.md)/`docs/specifications/*.md`. If none of these cover it, an ADR may be needed — full process, status values, and template are in [docs/decisions/README.md](docs/decisions/README.md); this section covers what that document doesn't.

- **When required:** a change alters a component boundary or interface, changes platform scope, or chooses between credible alternatives with real cost to reverse later — see that document's own "When to Write an ADR" for the complete criteria.
- **When not required:** routine documentation fixes, wording clarifications, or additive detail that doesn't change a decision already on record — including a new adapter/component that only applies patterns an existing ADR already established (see, e.g., the Storage Adapter's own "ADR Recommendation" section for a worked example of this judgment call).
- **Numbering:** the next number is one past the highest existing file in `docs/decisions/`. Because multiple agents may be working concurrently, treat this as a race condition, not a fact you can assume — check both the directory listing and recent/uncommitted git history for a number already claimed but not yet merged before writing the file. If you can't rule out a collision, say so rather than guessing.
- **Every new ADR, or status change to an existing one, updates [docs/decisions/README.md](docs/decisions/README.md)'s index in the same change** — a mismatched index is a defect, not a follow-up.
- **After any ADR is added or changes status, re-verify cross references** in documents that link to it — see [§ Documentation Workflow](#documentation-workflow).

## Multi-Agent Collaboration

Multiple AI agents — different tools, or repeated sessions of the same tool — may work in this repository at different times, and sometimes overlap.

- **Check `git status` before starting substantial work.** Uncommitted changes from another session are someone else's in-progress work, not clutter — see them before deciding what to touch.
- **Touch only what the task requires.** Don't "clean up" or refactor adjacent files as a side effect of an unrelated task.
- **Never overwrite a change you don't recognize.** If a file already has uncommitted or unexplained modifications relevant to your task, stop and report the overlap to the user rather than guessing whether it's safe to proceed or discard.
- **Keep progress visible on large, multi-file tasks**, using whatever mechanism the current tool provides for it — a task touching many files should be legible to whoever picks it up next, human or agent.

## Documentation Workflow

- **Verify internal links and heading anchors** after any structural edit (new headings, renamed files, moved sections) — a broken cross-reference in this heavily-linked documentation set is a defect, not a style nit.
- **Get explicit confirmation before a large documentation restructure** — new top-level sections, renamed files, new directories — rather than generating many files against an assumed shape.
- **A design document under `docs/` is not normative until accepted.** A file with a `Proposed` status banner (e.g. a `*_ADAPTER.md` design) describes a plan, not current architecture — don't treat it as settled, and don't implement against it, until its status says `Accepted` (and any ADR it required has also reached `Accepted`).
- **An accepted ADR is normative** for the decision it records, even before every document it affects has been updated to match — a document that still contradicts an `Accepted` ADR is a staleness bug to flag or fix, not a sign the ADR is optional.

## Repository Map

Full structure and the reasoning behind it: [docs/repository-organization.md](docs/repository-organization.md) — treat it as canonical, not this summary.

```
README.md, ARCHITECTURE.md, SPECIFICATION.md, ROADMAP.md    → normative docs, read first
CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, REVIEW.md → process/governance
CHANGELOG.md                                                 → Keep a Changelog, [Unreleased] section
docs/decisions/                                              → ADRs
docs/                                                        → deep documentation; see docs/README.md
config/                                                       → the ClassroomConfig contract
cli/                                                          → bcs CLI + the Platform Layer/Host Discovery
                                                                 subsystem it hosts — implemented/in-progress
                                                                 Python; the one place with real code, tests,
                                                                 and CI today
boot-manager/, builder/, deploy/                             → Phases 1-3; planning docs only, nothing implemented
```

If this list and `docs/repository-organization.md` ever disagree, that document wins.

## Conventions

Full detail lives in [docs/standards/](docs/standards/); summarized here so you don't need to fetch it for small edits:

- **Markdown style:** [docs/standards/markdown-style-guide.md](docs/standards/markdown-style-guide.md) — ATX headings (`#`), tables for structured requirements/matrices, [Mermaid](https://mermaid.js.org/) fenced code blocks for diagrams (used throughout `docs/architecture/`).
- **Requirement IDs:** reuse existing prefixes; don't invent a new one without updating `SPECIFICATION.md`'s structure. Canonical list and rules: [docs/standards/naming-conventions.md § Requirement IDs](docs/standards/naming-conventions.md#requirement-ids).
- **Commit messages:** [Conventional Commits](https://www.conventionalcommits.org/) (`docs:`, `feat:`, `fix:`, `chore:`, `adr:`), per [CONTRIBUTING.md](CONTRIBUTING.md).
- **Bash (Boot Manager, Builder, Deploy):** Bash is the primary implementation language for these three ([ADR-0004](docs/decisions/0004-bash-as-primary-implementation-language.md)); follow [docs/standards/bash-style-guide.md](docs/standards/bash-style-guide.md) — do not write it yet per Hard Constraint 1 above unless the user has explicitly confirmed the relevant component's phase has begun.
- **Python (`cli/` only):** the `bcs` CLI is Python 3.12 / Typer / Rich / Pydantic / PyYAML ([ADR-0007](docs/decisions/0007-python-for-the-bcs-cli.md)). See [§ Definition of Done](#definition-of-done) for what "finished" means, and [cli/README.md](cli/README.md) for exact commands.
- **Cross-referencing:** link between documents with relative Markdown links rather than duplicating content. If the same fact needs to live in two places, prefer linking from the more detailed doc back to the normative one.
