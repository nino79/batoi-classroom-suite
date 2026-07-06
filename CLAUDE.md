@AGENTS.md

# Claude Code — Repository Notes

This file is Claude Code's entry point for this repository. The vendor-neutral working agreement for any AI coding agent — scope, hard constraints, repository map, conventions — lives in [AGENTS.md](AGENTS.md) (imported above). This file adds only what's specific to running as Claude Code here.

## No Build/Test Commands Exist Yet

This repository is currently documentation and architecture only (see [ROADMAP.md](ROADMAP.md), Phase 0). There is no `package.json`, `Makefile`, or test runner to discover — don't search for one, and don't infer that its absence is an oversight. Once components reach implementation, this section will be updated with the real commands (linting, ShellCheck, tests) per [docs/processes/development-workflow.md](docs/processes/development-workflow.md).

## Working in This Repository

- Prefer `Read`/`Edit` for existing Markdown files over wholesale rewrites — most requests are incremental additions to an already-large, cross-linked documentation set. Re-check cross-references (relative links, heading anchors) after any structural edit, the same way the maintainers do — see [docs/standards/markdown-style-guide.md](docs/standards/markdown-style-guide.md).
- For any change touching `ARCHITECTURE.md`, `SPECIFICATION.md`, or a component interface, follow the ADR process in [docs/decisions/README.md](docs/decisions/README.md) before or alongside the change — don't edit those documents' normative content silently.
- Large documentation restructuring (new top-level sections, renamed files, new directories) is a good candidate for plan mode: confirm the shape with the user before generating many files.
- Use `TodoWrite` for any task touching more than a handful of files — this repository's own documentation set is large enough that multi-file edits benefit from explicit tracking, and it gives the user visibility into a task that produces many file-level tool calls before any single one is user-visible.

## Relationship to AGENTS.md

`AGENTS.md` is the project's durable, tool-agnostic contract for AI agents and is expected to be read by non-Claude tooling too. Keep Claude-specific operational detail (this file) separate from project-level constraints (`AGENTS.md`) — if a rule would make sense to a human contributor or a different AI tool, it belongs in `AGENTS.md`, not here.
