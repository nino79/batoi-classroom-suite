# Getting Started as a Contributor

This guide is for anyone new to Batoi Classroom Suite (BCS) who wants to contribute during the current [documentation and architecture phase](../../ROADMAP.md#phase-0--foundation-architecture--governance). If you're looking for end-user or operator documentation for running BCS in a classroom, note that this does not exist yet — it will follow implementation, per the [roadmap](../../ROADMAP.md).

## 1. Understand What Phase We're In

BCS is currently documentation-only: there is no installable software yet. Read [ROADMAP.md](../../ROADMAP.md) to see which phase is active and what's planned next. This matters because the most useful contribution right now is design review, not code.

## 2. Read in This Order

1. [README.md](../../README.md) — mission, components, target platform.
2. [ARCHITECTURE.md](../../ARCHITECTURE.md) — how Boot Manager, Builder, and Deploy fit together.
3. [SPECIFICATION.md](../../SPECIFICATION.md) — the requirements each component must satisfy.
4. The [glossary](../glossary.md), as needed, for terms like ESP, PXE, or partclone.
5. [docs/decisions/](../decisions/) — the reasoning behind decisions that are already settled, so you don't propose re-litigating them without new information.

## 3. Find Something to Work On

- Browse [open issues](https://github.com/nino79/batoi-classroom-suite/issues) labelled `good first issue` or filtered by [component](../../.github/LABELS.md#component).
- Spot a gap, contradiction, or unclear section in the docs? File it using the [documentation issue template](../../.github/ISSUE_TEMPLATE/documentation.yml).
- Have a design concern about an architectural choice? Check [docs/decisions/](../decisions/) first to see if it's already been considered; if not, see [CONTRIBUTING.md](../../CONTRIBUTING.md#proposing-an-adr) for how to propose an ADR.

## 4. Make Your Change

Follow the workflow in [CONTRIBUTING.md](../../CONTRIBUTING.md): branch, commit using [Conventional Commits](https://www.conventionalcommits.org/), and open a pull request using the [PR template](../../.github/PULL_REQUEST_TEMPLATE.md).

## 5. Ask Questions

If something is unclear and you can't find the answer in the docs above, open a [GitHub Discussion](https://github.com/nino79/batoi-classroom-suite/discussions) or a question-context issue (see [.github/ISSUE_TEMPLATE/config.yml](../../.github/ISSUE_TEMPLATE/config.yml)). Unclear documentation is itself a bug worth reporting — if you're confused, the next reader probably will be too.

See also: [docs/guides/faq.md](faq.md) for answers to common questions about the project's scope and direction.
