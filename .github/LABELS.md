# Label Taxonomy

This document defines the GitHub label set used across BCS issues and pull requests. It's the source of truth maintainers use to (re)create labels in the repository settings — GitHub does not version labels as files, so this document is what keeps the taxonomy consistent and reviewable.

Each label follows the pattern `category: value` so they sort and scan predictably in the GitHub UI.

## Type

What kind of item this is.

| Label | Color | Description |
|---|---|---|
| `type: bug` | `#d73a4a` | Something is incorrect, inconsistent, or broken (including in documentation). |
| `type: feature` | `#a2eeef` | A new capability or requirement proposal. |
| `type: documentation` | `#0075ca` | Documentation gap, clarity issue, or improvement. |
| `type: adr` | `#5319e7` | An Architecture Decision Record proposal or discussion. |
| `type: question` | `#d876e3` | A question that isn't a bug report or feature proposal. |
| `type: chore` | `#cfd3d7` | Maintenance work with no functional or documentation-content change (tooling, labels, templates). |

## Component

Which part of BCS this affects. Mirrors [ARCHITECTURE.md](../ARCHITECTURE.md).

| Label | Color | Description |
|---|---|---|
| `component: boot-manager` | `#1d76db` | Boot Manager. |
| `component: builder` | `#0e8a16` | Builder. |
| `component: deploy` | `#fbca04` | Deploy. |
| `component: architecture` | `#5319e7` | Cross-component architecture or interfaces. |
| `component: docs` | `#0075ca` | Documentation set under `docs/` or top-level `.md` files. |
| `component: repo-tooling` | `#cfd3d7` | `.github/` templates, labels, repository configuration. |

## Priority

Used during triage; not every issue needs one immediately.

| Label | Color | Description |
|---|---|---|
| `priority: critical` | `#b60205` | Blocks the current roadmap phase or represents a security concern. |
| `priority: high` | `#d93f0b` | Should be addressed in the current phase. |
| `priority: medium` | `#fbca04` | Valuable, not urgent. |
| `priority: low` | `#c2e0c6` | Nice to have; unscheduled. |

## Status

Workflow state, applied and updated by maintainers during triage.

| Label | Color | Description |
|---|---|---|
| `status: triage` | `#ededed` | Newly opened, not yet reviewed by a maintainer. |
| `status: accepted` | `#0e8a16` | Reviewed and agreed to be in scope. |
| `status: in-progress` | `#fbca04` | Actively being worked on. |
| `status: blocked` | `#b60205` | Waiting on another issue, ADR, or external decision. |
| `status: needs-discussion` | `#d876e3` | Requires maintainer/community discussion before proceeding, often ADR-worthy. |
| `status: wontfix` | `#ffffff` | Declined, with reasoning recorded in the issue. |

## Difficulty / Community

For encouraging external contribution.

| Label | Color | Description |
|---|---|---|
| `good first issue` | `#7057ff` | Well-scoped and suitable for a first-time contributor. |
| `help wanted` | `#008672` | Maintainers are explicitly looking for help on this. |

## Usage Notes

- Every issue should get exactly one `type:` label and at least one `component:` label during triage.
- `priority:` and `status:` labels are applied by maintainers, not requesters — don't self-assign a priority in a new issue.
- Issue templates in [.github/ISSUE_TEMPLATE/](ISSUE_TEMPLATE/) pre-apply the relevant `type:` and `status: triage` labels automatically.
