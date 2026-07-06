# Contributing to Batoi Classroom Suite

Thank you for considering a contribution to BCS. This project is currently in its **architecture and specification phase** (see [ROADMAP.md](ROADMAP.md)), which means the most valuable contributions right now are about *getting the design right*, not shipping code. That will change as components move into implementation — this guide covers both.

## Ground Rules

- All communication, code, comments, and documentation in this repository are in **English**.
- Be respectful and constructive. This project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
- Discuss significant changes before implementing them. Open an issue or a draft PR early rather than presenting a large, finished change.

## Ways to Contribute During the Documentation Phase

1. **Review the architecture.** Read [ARCHITECTURE.md](ARCHITECTURE.md) and [SPECIFICATION.md](SPECIFICATION.md) and challenge assumptions, especially around the UEFI/NVMe/Clonezilla platform choices — these are expensive to change once implementation starts.
2. **Propose an Architecture Decision Record (ADR).** If you're proposing something that changes a component boundary, an interface, or a platform assumption, write it up as an ADR rather than editing prose documents directly. See [docs/decisions/README.md](docs/decisions/README.md) for the process and template.
3. **Improve documentation.** Fix ambiguity, add missing detail to specifications, expand the [glossary](docs/glossary.md), or improve the [guides](docs/guides/).
4. **File well-scoped issues.** Use the issue templates (bug, feature, documentation) so reports and proposals are triaged consistently. See [.github/LABELS.md](.github/LABELS.md) for how issues get labelled.

## Contributing Code (Once Implementation Begins)

As components move from specification into implementation (see [ROADMAP.md](ROADMAP.md)), the following applies:

- Each component (`boot-manager/`, `builder/`, `deploy/`) is developed against its own specification in `docs/specifications/`. Changes should trace back to a requirement ID (e.g. `BM-004`) or update the specification alongside the code.
- Keep components decoupled: code in one component must not directly depend on another component's internals — only on the interfaces described in [ARCHITECTURE.md §4](ARCHITECTURE.md#4-component-boundaries).
- Follow [docs/standards/coding-standards.md](docs/standards/coding-standards.md) and, since Bash is the primary implementation language ([ADR-0004](docs/decisions/0004-bash-as-primary-implementation-language.md)), [docs/standards/bash-style-guide.md](docs/standards/bash-style-guide.md).
- New behaviour needs an entry in [CHANGELOG.md](CHANGELOG.md) under "Unreleased," following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Workflow

The summary below is enough for most contributions; see [docs/processes/development-workflow.md](docs/processes/development-workflow.md) for the full reference (branching model, CI expectations, merge strategy) and [docs/processes/release-process.md](docs/processes/release-process.md) for how releases are cut.

1. **Fork and branch.** Branch names follow `type/short-description`, per [docs/standards/naming-conventions.md](docs/standards/naming-conventions.md#git-branches): `docs/boot-manager-fallback-clarify`, `adr/clonezilla-alternatives`, `feat/deploy-multicast-retry`.
2. **Commit messages.** Follow [Conventional Commits](https://www.conventionalcommits.org/): `docs:`, `feat:`, `fix:`, `chore:`, `adr:` prefixes. Example: `docs(spec): clarify BLD-005 reproducibility scope`.
3. **Open a pull request** using the [PR template](.github/PULL_REQUEST_TEMPLATE.md). Link the issue or ADR it addresses.
4. **Review.** At least one maintainer approval is required before merge. For changes touching `ARCHITECTURE.md`, `SPECIFICATION.md`, or component interfaces, an accompanying ADR is expected.
5. **Documentation style.** Follow [docs/standards/markdown-style-guide.md](docs/standards/markdown-style-guide.md), including its conventions for Mermaid diagrams.
6. **Definition of Done for documentation changes:** the change is internally consistent with the rest of the docs set (cross-references updated), uses English throughout, and — for normative changes — updates requirement IDs and the roadmap where relevant.

## Proposing an ADR

See the full process in [docs/decisions/README.md](docs/decisions/README.md). In short:

1. Copy the template referenced there into a new file `docs/decisions/NNNN-short-title.md`.
2. Describe the context, the decision, and the consequences — including what you're explicitly *not* deciding.
3. Open it as a PR for discussion; it is merged once the relevant maintainers agree, even if the decision is "we chose X over Y for now."

## Getting Help

If you're new to the project, start with [docs/guides/getting-started.md](docs/guides/getting-started.md). For questions that aren't bug reports or feature proposals, use [GitHub Discussions](https://github.com/nino79/batoi-classroom-suite/discussions) — see [.github/DISCUSSIONS.md](.github/DISCUSSIONS.md) for which category to use — or open an issue via [.github/ISSUE_TEMPLATE/config.yml](.github/ISSUE_TEMPLATE/config.yml).
