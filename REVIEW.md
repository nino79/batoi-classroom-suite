# Architecture Review — Batoi Classroom Suite (BCS)

**Reviewer role:** Principal Software Engineer, independent architecture review
**Scope:** Full repository as it stands prior to any implementation
**Method:** Read every root document, the full `docs/` tree, `.github/` templates, and component placeholders; cross-checked claims against actual repository state (git history, file inventory, tooling config presence)

This review is deliberately unsparing. The goal is to surface what will hurt in year two through year ten, not to validate the effort that went into the documentation set. A large, polished documentation set is not the same thing as a sound architecture, and the two are evaluated separately below.

---

## Score: 6.0 / 10

| Category | Score | Rationale |
|---|---|---|
| Documentation craftsmanship | 8 / 10 | Consistent structure, working cross-references, genuine traceability between requirements and design docs. |
| Architectural rigor | 5 / 10 | Component boundaries are clear; the single most important interface in the whole system is undefined. |
| Security & privacy | 3 / 10 | No threat model, no data-protection treatment for a public-education deployment, no supply-chain trust story. |
| Scalability alignment | 4 / 10 | The mission claims a scale the specification doesn't address. |
| Governance & sustainability | 3 / 10 | Single contributor, no CODEOWNERS, no succession story, for a project explicitly framed as 10-year infrastructure. |
| Process maturity vs. enforcement | 5 / 10 | Extensive standards are documented; none are enforced or enforceable yet. |
| Proportionality (effort vs. output) | 5 / 10 | 47 Markdown files and ~2,100 lines of documentation exist against zero lines of code — a real methodology risk, discussed below. |

A 6.0 reflects a genuinely well-organized *documentation exercise* sitting on top of an *incomplete architecture*. Nothing here is unrecoverable, but several of the gaps below are exactly the kind that are cheap to fix now and expensive to fix after Boot Manager, Builder, and Deploy have working code that depends on the current ambiguity.

---

## 1. Architectural Problems

### 1.1 The system's central interface is undefined — and everything depends on it

The maintenance-request handshake between Boot Manager and Deploy (`BM-006` / `DEP-006`) is the *only* runtime interface between two of the three components (Builder → Deploy is a one-shot artifact handoff; this one is live and bidirectional). It is referenced as an interface contract in `ARCHITECTURE.md §4`, in both components' specifications, and in both components' architecture docs — and in every single one of those places it is flagged as an **open question** with no schema, no transport, and no owner.

This is not a minor gap. A "stable machine identifier" is a prerequisite for `BM-006`, `DEP-004`, `DEP-005`, `DEP-006`, and arguably the entire auditability requirement `NFR-004` — and `docs/architecture/boot-manager.md` states plainly that its format is undecided. Four ADRs exist (component split, Clonezilla choice, Bash choice, the ADR process itself), and none of them addresses the one design decision that actually couples two components together at runtime. **This should have been ADR-0002 or ADR-0003, not an unresolved footnote.**

### 1.2 No storage/hosting architecture for the golden image artifact

`BLD-002` says Builder "must produce a versioned image artifact." `DEP-001` says Deploy consumes "the same golden image artifact." Nowhere in `ARCHITECTURE.md`, `docs/architecture/builder.md`, or `docs/architecture/deploy.md` is there any mention of *where that artifact lives between the two components* — no artifact repository, no file server, no object storage, no retention policy, no size budget. For a system whose entire value proposition is "Builder hands Deploy a versioned artifact," the thing being handed over has no defined home. This also means `BLD-006`'s "build provenance" has no described storage location for Deploy to query against at verification time (`DEP-004`) — the architecture docs even admit this directly ("where build provenance records are stored... is an open question," `docs/architecture/builder.md`).

### 1.3 Physical/network topology is entirely absent

Every diagram in this repository (9 Mermaid diagrams total) is a logical component or sequence diagram. None shows the actual physical deployment topology: where the Deploy server sits relative to the classroom switch, how DHCP/PXE chainloading is provisioned, whether one Deploy instance serves one classroom or a whole centre, or what happens when two classrooms attempt simultaneous multicast sessions on a shared backbone. `PLAT-007` asserts a "wired classroom LAN capable of PXE network boot and IP multicast" as a bare assumption with no accompanying network architecture. This is the diagram a network-literate reviewer would look for first, and it doesn't exist.

### 1.4 The mission statement and the specification describe two different systems

`README.md` opens with a mission to serve "hundreds of classroom PCs" across "school years, hardware refresh cycles." `SPECIFICATION.md` (`NFR-002`) defines the actual performance target as "20–30 machines on a single switch" — i.e., one classroom. Multi-classroom and multi-centre orchestration is deferred to a single unexplained bullet in `ROADMAP.md` Phase 5 ("Multi-classroom / multi-centre deployment orchestration — 💤 Not started") with zero design content anywhere in the architecture docs.

This isn't inherently wrong — phased scope is reasonable — but the documentation set doesn't own the gap. It states an ambitious mission and a narrow specification side by side without ever saying "the specification only covers a fraction of the mission today, and here's why that's fine for now." A reader (or a funder, or a partner school) comparing the two documents would reasonably conclude the project is over-promising.

### 1.5 No performance engineering behind the one hard performance requirement

`DEP-007` asserts a full-classroom deployment "SHOULD complete within a single class period." There is no supporting calculation anywhere — no assumed image size, no assumed network throughput, no math showing why 20–30 machines over multicast on an unspecified switch class fits in ~50 minutes. A requirement with a real-world time bound and zero engineering justification is a requirement someone made up to sound concrete. It needs a capacity-planning worksheet, not just an assertion.

---

## 2. Documentation Gaps

- **No security threat model.** `SECURITY.md` lists "security-relevant design areas" as prose bullets (boot integrity, image provenance, network trust) but there is no actual threat model (assets, actors, attack trees, trust boundaries) anywhere in `docs/`. For a system that reflashes the OS of every machine in a public school computer lab over the network, "we thought about trust a bit" is not sufficient rigor.
- **No data protection / privacy treatment.** This is a public-education deployment platform (LliureX, CIPFP Batoi, Valencian public schools). Student and staff data protection (Spanish LOPD/GDPR obligations) is never mentioned once across 47 files — not in `SECURITY.md`, not in `SPECIFICATION.md`'s non-functional requirements, nowhere. If Deploy or Boot Manager ever touch student home directories, profiles, or identifiers, this is a compliance gap, not a nice-to-have.
- **No supply-chain trust story for Builder.** `BLD-005`/`BLD-006` cover reproducibility and provenance of BCS's *own* artifact, but nothing addresses trust in the upstream Ubuntu/LliureX package mirrors Builder pulls from — no mention of APT signature verification, mirror integrity, or what happens if an upstream package repository is compromised or a point release silently changes package content underneath a "pinned" recipe.
- **No accessibility requirements.** `BM-007` requires Valencian/Spanish text but says nothing about accessibility (screen-reader compatibility, high-contrast theming, keyboard-only navigation) for a boot menu that is, by definition, run in an environment without the assistive tooling of a full desktop session. In a public-sector education product this is a real omission, not a stretch requirement.
- **No disaster recovery / backup story.** If the golden image repository (whose location is itself undefined, see §1.2) is lost, there is no documented recovery path. If a Deploy session's logs are the only audit trail (`NFR-004`) and that log store isn't backed up, an incident is unrecoverable-by-design.
- **No hardware/asset inventory model.** Deploy operates against "a classroom fleet," but nothing describes how machines are registered, tagged, or looked up — this is the same gap as §1.1 (the undefined machine identifier) viewed from the operations side rather than the interface side.
- **No internationalization mechanism.** `BM-007`/`NFR-006` require Valencian and Spanish UI text but no i18n framework, string-catalog format (gettext/PO, JSON locale files, etc.), or translation contribution workflow is specified anywhere, including in the otherwise-detailed `docs/standards/`.
- **No traceability matrix.** Each requirement has an ID; nothing maps requirement IDs to test cases, issues, or acceptance evidence in one place. `docs/specifications/*.md` add prose "Acceptance" bullets per requirement, but there's no table a reviewer (or an auditor) can scan to see requirement → test → status.

---

## 3. Duplicated Concepts

The documentation set violates its own stated single-sourcing principle (`docs/repository-organization.md §Placement Rules`, rule 1: *"Anything that explains, justifies, or expands on a requirement belongs under `docs/`, linked back from the root document, never duplicated into it"*) in practice:

- **Component responsibilities are stated in full four times**: once in `ARCHITECTURE.md §3`, once in `docs/architecture/<component>.md §Responsibilities`, once in `docs/specifications/<component>.md`, and once again in `<component>/README.md §Scope`. Each is a close paraphrase of the same bullet list of requirement IDs. This is not "linking to a canonical source," it's restating the same content in four places with four opportunities to drift out of sync as requirements evolve.
- **"Recipe" vs. "manifest."** `BLD-001` and every downstream document refer to Builder's input as "recipe/manifest" — the project never picked one term. `docs/glossary.md` defines "Recipe (Image Recipe / Manifest)" as a single entry, formalizing the ambiguity rather than resolving it. A specification should not have two names for its most important input artifact.
- **The three-component rationale is told three times.** `ARCHITECTURE.md §4`, `ADR-0002`, and `docs/architecture/overview.md` each re-argue why Boot Manager, Builder, and Deploy are separate, with overlapping but not identical reasoning each time. The ADR should be the single canonical argument; the other two should link to it in one sentence, not re-derive it.
- **Label and Discussion category documentation both self-acknowledge they require manual synchronization** (`.github/LABELS.md`, `.github/DISCUSSIONS.md`) with no tooling to enforce that sync — this is really a maintainability risk (§5) but it's also a duplicated-source-of-truth problem: the real labels live in GitHub's settings UI, and the Markdown file is a second, driftable copy of the same information by construction.

---

## 4. Scalability Risks

- **Multicast-per-classroom is the only deployment model considered.** There is no design for concurrent multi-classroom sessions sharing backbone bandwidth, no discussion of a deployment server hierarchy for a whole centre, and no discussion of what "hundreds of classroom PCs" (the mission statement) implies for Deploy's architecture beyond a single unstarted roadmap bullet.
- **Reproducibility (`BLD-005`) is asserted against a moving upstream target.** Ubuntu 24.04 and LliureX 23 both receive point releases and security updates over a 10-year horizon; nothing pins *which* point-in-time mirror snapshot a recipe builds against, so "reproducible" is aspirational rather than engineered.
- **No migration/upgrade path for the golden image lineage.** The `v1.0` roadmap milestone lists "Migration/upgrade path for existing classrooms" as an unstarted bullet with no design — for infrastructure meant to survive multiple LliureX major versions, this is a first-class architectural concern, not a v1.0 afterthought.
- **Session concurrency and resource contention are unaddressed.** `NFR-001`'s resumability requirement covers a single session's internal failure handling, but nothing addresses what happens when two classrooms' Deploy sessions compete for the same multicast-capable network segment.

---

## 5. Maintainability Concerns

- **Bus factor of one.** `git log` shows a single human contributor across two committer identities. There is no `CODEOWNERS`, no `MAINTAINERS.md`, and no documented process for adding a second maintainer. A project explicitly pitched (in this very review's brief) as something to be "maintained for at least the next 10 years" cannot rely on tribal knowledge held by one person with no succession plan. This is arguably the single biggest sustainability risk in the repository, and it isn't mentioned anywhere in `GOVERNANCE`-adjacent documentation because no governance document exists beyond a Code of Conduct.
- **Standards are documented but not enforced.** `docs/standards/bash-style-guide.md` and `docs/standards/markdown-style-guide.md` both explicitly defer enforcement to "once CI exists" — but there is no `.shellcheckrc`, no `.markdownlint.json`, no `.editorconfig`, and no CI workflow anywhere in the repository. Every convention in `docs/standards/` is currently aspirational; the moment a second contributor joins, drift begins immediately and silently, because nothing will catch it.
- **The README contradicts the project's own style guide.** `docs/standards/markdown-style-guide.md` explicitly instructs: *"Avoid marketing language ('blazing fast', 'seamless')... this is infrastructure documentation for technicians and contributors, not a product page."* `README.md`'s very first line describes BCS as an **"enterprise-grade deployment platform"** — unsupported marketing language, in the one document every reader sees first, directly contradicting a rule the project wrote for itself. If the standards aren't followed in the flagship document, they won't survive contact with a second contributor either.
- **Vanity badges.** The `README.md` badge row includes a "Contributions Welcome" badge and a hand-set "status" badge — neither reflects any automated or verifiable state (there is no CI, so there is nothing a badge could actually report on). This is a cosmetic issue, but it's the kind of cargo-culted signal that erodes trust in a repository's other, more substantive claims once a careful reader notices it.
- **ADR template is not actually a template.** `CONTRIBUTING.md` and `docs/decisions/README.md` both instruct contributors to "copy ADR-0001 as a template," but ADR-0001 is a real, filled-in decision record about *why ADRs exist* — using it as a fill-in-the-blank template means every new ADR starts by copying prose that has nothing to do with the new decision. A dedicated `TEMPLATE.md` (with placeholder text) is missing.
- **Four asset subdirectory READMEs carry near-zero unique content.** `assets/backgrounds/README.md`, `fonts/README.md`, `icons/README.md`, and `logos/README.md` are each a two-line restatement of `assets/README.md`. This is documentation-for-documentation's-sake and adds to review burden without adding information.

---

## 6. Missing Standards

- **No `.editorconfig`**, despite multiple documents emphasizing formatting consistency.
- **No pinned tool versions.** `bash-style-guide.md` references ShellCheck, `shfmt`, and `bats` without pinning versions — for a decade-long project, "whatever version is installed when someone runs it" is not a reproducibility story.
- **No minimum Bash version stated.** The style guide assumes Bash-specific features (arrays, `[[ ]]`) but never states a minimum version (e.g., Bash 4.4+ for associative array features that may be used later), which matters given LliureX/Ubuntu ship specific defaults that will themselves change over a 10-year window.
- **No license-compatibility analysis.** BCS is MIT-licensed; Clonezilla and its dependencies are GPL-licensed. `ADR-0003` justifies *choosing* Clonezilla but never addresses the licensing implications of orchestrating or bundling GPL-licensed tooling from an MIT project — this needs at least one paragraph of legal/licensing due diligence, not silence.
- **No versioning policy for the specification itself, separate from the software.** `CHANGELOG.md` states that pre-1.0 version numbers "track the maturity of the specification, not a shipped release" — but `docs/processes/release-process.md`'s SemVer policy is written entirely in terms of software interfaces (MAJOR/MINOR/PATCH tied to component interfaces). These two framings are not reconciled: is `v0.3.0` a documentation milestone or a software milestone? The project has two different, unreconciled answers in two different files.
- **No defined roles/RACI.** "The technician," "the maintainer," and "the contributor" are all used informally throughout the docs with no single place defining who holds which responsibility — relevant given `docs/architecture/overview.md`'s stated design principle is literally "a single technician is the operator."

---

## 7. A Meta-Concern: Proportionality

47 Markdown files, ~2,100 lines of documentation, 4 ADRs, a full label taxonomy, Discussions categories, and a style guide for a language (Bash) in which not one line has been written — against zero lines of implementation code and zero prototypes validating any of the harder claims (`DEP-007`'s performance target, `BLD-005`'s reproducibility target, whether Clonezilla's multicast mode actually behaves as described on real classroom hardware).

This is a real risk, not just an aesthetic one: **Big Design Up Front (BDUF) at this scale, before a single spike or prototype has touched real UEFI/NVMe hardware, tends to produce specifications that are confidently wrong about the hard parts** (see §1.5 — the one hard performance number in the entire spec has no supporting evidence) while being exhaustively, correctly detailed about the easy parts (label colors, commit message formats, Discussion category names). The easy parts got the same — or more — attention as the one unresolved cross-component interface that everything else depends on (§1.1). That imbalance is the clearest signal in this repository that documentation effort and architectural risk were not prioritized together.

---

## 8. Recommendations Before Implementation Begins

In priority order — the first three should block starting Boot Manager or Deploy implementation; the rest should happen in parallel with early implementation, not after it:

1. **Design and ADR the Boot Manager ↔ Deploy interface now.** Define the machine identifier scheme, the request/response schema (even a simple one), and the transport, and write it as an ADR. This is the one piece of missing design that blocks meaningful work on two of the three components.
2. **Define the artifact storage/hosting architecture** for the golden image between Builder and Deploy — even a deliberately simple answer ("a single NFS share, one centre, v1.0 only") is better than silence, and it directly unblocks `BLD-006`/`DEP-004`'s provenance verification design.
3. **Run one real spike before finalizing `DEP-007`.** Build a throwaway image, multicast it to a handful of real (or virtualized) NVMe/UEFI machines, and replace the unsupported performance assertion with a number backed by a measurement — or an explicit calculation with stated assumptions.
4. **Add a minimal threat model to `SECURITY.md`**: assets, trust boundaries (classroom LAN, PXE/multicast traffic, the artifact store), and at least the top three attack scenarios (rogue PXE server, tampered image in transit, spoofed maintenance request).
5. **Add a data-protection section** addressing whether student/staff data ever transits Boot Manager or Deploy, and if so, under what legal basis (Spanish/EU education-sector data protection law).
6. **Resolve the mission-vs-specification scope gap explicitly** — either narrow the README's stated ambition to match the current roadmap honestly, or add a real (even if thin) multi-classroom architecture section instead of a single unstarted bullet.
7. **Stand up minimal enforcement before or alongside the first code**: `.shellcheckrc`, `.markdownlint.json`, `.editorconfig`, and a basic CI workflow that runs them. Documented-but-unenforced standards decay the moment a second contributor shows up.
8. **Fix the README's marketing language** to comply with the project's own Markdown style guide, and replace the vanity badges with either real, automatically-updated badges or no badges at all.
9. **Add `CODEOWNERS` and a one-paragraph succession/bus-factor statement** — even "there is currently one maintainer; here's what happens if they're unavailable" is more honest and more useful than silence, for a project explicitly framed on a 10-year horizon.
10. **Collapse the four-layer duplication of component responsibilities** down to one canonical source (`SPECIFICATION.md`/`ARCHITECTURE.md`) with the other three layers reduced to a one-line pointer, and pick one term — "recipe" or "manifest," not both.
11. **Split the ADR template out of ADR-0001** into a real `docs/decisions/TEMPLATE.md`.

None of this invalidates the work that exists — the internal consistency, the cross-referencing discipline, and the clarity of the writing are genuinely above average for a project at this stage. But a Principal Engineer's job is to ask "what breaks in year three," and on that question, this repository currently has more polish than substance where it counts most: the one interface every component depends on, the one hard performance number in the spec, and the one-person governance model underneath a ten-year commitment.
