# GitHub Discussions Categories

BCS uses [GitHub Discussions](https://github.com/nino79/batoi-classroom-suite/discussions) for open-ended conversation that doesn't belong in Issues (actionable, trackable work) or in a formal [ADR](../docs/decisions/) (a decision ready to be proposed). This document is the source of truth for which categories should exist and what each is for — like [LABELS.md](LABELS.md), it's a specification a maintainer applies in repository settings, since categories aren't version-controlled files.

## Why Discussions, Separate from Issues

| | Issues | Discussions |
|---|---|---|
| Use for | A concrete bug, a scoped feature request, a documentation defect — something with a clear "done" state | Open-ended questions, early-stage ideas, community conversation |
| Lifecycle | Triaged, labelled, closed when resolved | Can stay open indefinitely; resolved by consensus, not by a merge |
| Output | A code/doc change, or a decision to decline | Sometimes nothing formal; sometimes graduates into an Issue or an ADR |

If a Discussion produces a concrete, scoped piece of work, open an Issue that links back to it. If it produces an architectural decision, write an ADR (see [CONTRIBUTING.md](../CONTRIBUTING.md#proposing-an-adr)) that references it.

## Categories

| Category | Format | Purpose |
|---|---|---|
| **Announcements** | Announcement (maintainer-only posting) | Release notes highlights, roadmap phase transitions, and other maintainer-to-community broadcasts. Mirrors entries in [CHANGELOG.md](../CHANGELOG.md) and [ROADMAP.md](../ROADMAP.md) but in prose form. |
| **Q&A** | Question/Answer | "How do I..." / "Why does..." questions that aren't documentation bugs. If the same question comes up twice, that's a signal the answer belongs in [docs/guides/faq.md](../docs/guides/faq.md) instead. |
| **Ideas** | Open-ended discussion | Early-stage feature or scope ideas that aren't yet well-defined enough for a Feature Request issue. Use this before, not instead of, the [feature request template](ISSUE_TEMPLATE/feature_request.yml) once an idea is concrete. |
| **Architecture & RFCs** | Open-ended discussion | Pre-ADR design conversation — the place to float an architectural change and gather feedback *before* writing a formal ADR under [docs/decisions/](../docs/decisions/). Once a proposal has converged, it should be written up as an ADR pull request, per [docs/decisions/README.md](../docs/decisions/README.md). |
| **Show and Tell** | Open-ended discussion | Centres or individuals sharing how they've deployed or adapted BCS — classroom photos, hardware notes, local customisations. Purely community-facing; not a support channel. |
| **General** | Open-ended discussion | Anything that doesn't fit the categories above. If General accumulates a recurring topic, that's a signal to add a dedicated category. |

## Moderation Notes

- **Announcements** is restricted to maintainers to keep it a reliable, low-noise signal.
- Discussions that go stale without resolution are not closed the way Issues are — they may be locked after a long period of inactivity, but are kept for historical/searchable context rather than deleted.
- Security vulnerabilities must **never** be raised in Discussions — see [SECURITY.md](../SECURITY.md#reporting-a-vulnerability) for private reporting.

## Setup Checklist (for maintainers)

Discussions must be enabled in repository Settings → General → Features, and the categories above created/renamed to match this document under Settings → Discussions. Keep this file and the live category list in sync when either changes.
