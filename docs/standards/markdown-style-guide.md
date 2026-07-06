# Markdown Style Guide

BCS is, at this stage, almost entirely documentation — so conventions for how that documentation is written matter as much as code style will later. This guide governs every `.md` file in this repository.

## Headings

- One `#` (H1) per document, matching the document's title, as the first line.
- ATX style (`#`, `##`, `###`) exclusively — never Setext-style (`===`/`---` underlines).
- Title Case for the H1 and H2 level ("Repository Organization", "Grouping Model"); sentence case is acceptable for more granular H3+ headings where Title Case would feel forced.
- Don't skip levels (an H3 must be under an H2, not directly under the H1).

## Structure and Cross-Referencing

- Prefer linking to the canonical source of a fact over restating it. If the same requirement, definition, or decision needs to appear in two places, one of them should be a link, not a copy — see the "normative vs. descriptive" placement rule in [repository-organization.md](../repository-organization.md#placement-rules).
- Use relative links between files in this repository (`[text](../other-doc.md)`), never absolute `https://github.com/...` URLs for content that lives in the same repository — relative links survive forks and renames of the org/repo.
- Link to a heading anchor (`file.md#some-heading`) when referencing a specific section rather than a whole document.
- On first mention of a domain term in a document, consider linking it to its entry in [docs/glossary.md](../glossary.md).

## Requirement IDs and Code-Like Tokens

- Requirement IDs (`BM-004`, `DEP-007`, `NFR-002`), file paths, commands, and identifiers are wrapped in backticks: `` `BM-004` ``, not *BM-004* or plain BM-004.
- Requirement ID prefixes are fixed — see [naming-conventions.md](naming-conventions.md#requirement-ids) — don't invent a new prefix without updating that document.

## Tables

- Used for structured, scannable comparisons: requirement lists, compatibility matrices, label taxonomies. If a table would only have one column of real content, it should probably be a bullet list instead.
- Keep table cells to a sentence or two; long explanations belong in prose below the table, referenced from it if needed.

## Code Fences

- Always tag the language: ` ```bash `, ` ```yaml `, ` ```mermaid `, ` ```text ` for plain trees/output. An untagged fence is a style bug, not a stylistic choice.
- Directory trees use a plain (` ```text ` or untagged-but-consistent, per existing convention in this repo) fence with box-drawing characters (`├──`, `└──`), matching the trees already in `README.md` and [repository-organization.md](../repository-organization.md).

## Mermaid Diagrams

Mermaid diagrams are encouraged wherever a relationship, sequence, or state machine is easier to read than to parse from prose — BCS's architecture documents use `flowchart`, `sequenceDiagram`, and `stateDiagram-v2` extensively. Conventions:

- Fence with ` ```mermaid `, and keep one diagram's *purpose* singular — a diagram trying to show component boundaries *and* a detailed sequence at once should be split into two.
- Label every node and edge meaningfully; avoid bare IDs like `A`, `B` without a `[readable label]`.
- A diagram supplements the surrounding prose, it doesn't replace it — always introduce the diagram with a sentence explaining what it shows, and follow complex diagrams with prose walking through anything non-obvious.
- Prefer `flowchart LR`/`TB` for structural/data-flow relationships, `sequenceDiagram` for time-ordered interactions between components, and `stateDiagram-v2` for a single component's internal states (e.g., Boot Manager's boot paths).
- Keep diagrams renderable in plain GitHub Markdown preview — don't rely on Mermaid features outside what GitHub's built-in renderer supports.

## Line Length and Prose Style

- No hard line-wrap requirement — write in full sentences and let editors soft-wrap; don't manually break lines mid-sentence.
- Prefer active voice and direct statements ("Deploy verifies the checksum") over passive hedging ("the checksum may be verified by Deploy").
- Avoid marketing language ("blazing fast", "seamless") — this is infrastructure documentation for technicians and contributors, not a product page.

## File Naming

See [naming-conventions.md](naming-conventions.md#files-and-directories) for the authoritative rule: `kebab-case.md`, except the fixed set of root governance files that follow the `UPPERCASE.md` GitHub convention (`README.md`, `ARCHITECTURE.md`, etc.).

## Tooling

Once CI exists for this repository, [markdownlint](https://github.com/DavidAnson/markdownlint) is expected to enforce heading structure, fence language tags, and link syntax automatically. Until then, reviewers check this guide manually as part of the pull request checklist (see [.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md)).
