@AGENTS.md

# Claude Code — Repository Notes

This file is Claude Code's entry point for this repository. [AGENTS.md](AGENTS.md) (imported above) is the authoritative, tool-agnostic contract for every AI coding agent working here — scope, hard constraints, workflow, and conventions all live there. This file adds only what's specific to running as Claude Code: its own tools and features, nothing a different agent or a human contributor would also need to know.

## Working in This Repository

- **Plan Mode.** Large documentation restructuring (new top-level sections, renamed files, new directories) is a good candidate for Plan Mode — confirm the shape with the user before generating many files. This is Claude Code's own mechanism for [AGENTS.md § Documentation Workflow](AGENTS.md#documentation-workflow)'s "confirm before a large restructure" rule.
- **TodoWrite.** Use it for any task touching more than a handful of files — this repository's own documentation set is large enough that multi-file edits benefit from explicit tracking, and it gives the user visibility into a task that produces many file-level tool calls before any single one is user-visible. This is Claude Code's own mechanism for [AGENTS.md § Multi-Agent Collaboration](AGENTS.md#multi-agent-collaboration)'s "keep progress visible" rule.

## Relationship to AGENTS.md

See [AGENTS.md § Tool Precedence](AGENTS.md#tool-precedence): AGENTS.md is authoritative, and this file may only add Claude Code-specific operational detail — it must never restate or contradict a project-wide rule. If a rule would make sense to a human contributor or a different AI tool, it belongs in AGENTS.md, not here.
