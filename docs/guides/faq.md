# Frequently Asked Questions

## Is there any working software yet?

No. As of this writing, BCS is in [Phase 0](../../ROADMAP.md#phase-0--foundation-architecture--governance): architecture and specification only. `boot-manager/`, `builder/`, and `deploy/` contain planning documentation, not code. See [ROADMAP.md](../../ROADMAP.md) for what comes next.

## Why not just use Clonezilla directly, without BCS?

Clonezilla is the deployment engine BCS's Deploy component orchestrates (see [ADR-0003](../decisions/0003-clonezilla-as-deployment-engine.md)) — BCS isn't a replacement for it. Clonezilla alone answers "how do I clone a disk," but not "how do I build a reproducible, versioned golden image," "how do I manage the boot-time experience across a fleet of machines that changes over time," or "how do I let a machine request its own re-imaging without a technician walking over to it." Those are the problems Builder and Boot Manager exist to solve around Clonezilla.

## Why is the platform target so specific (LliureX 23, Ubuntu 24.04, UEFI, NVMe)?

Because genericity has a real cost, and BCS doesn't have a customer for "any Linux, any hardware" — see the "specific over generic" principle in [docs/architecture/overview.md](../architecture/overview.md#design-principles). Narrowing the target lets the specification make concrete, testable claims (e.g., `DEP-007`'s performance target) instead of hedged ones. If the target platform needs to expand later, that's a deliberate, ADR-worthy decision, not a default.

## Why three separate components instead of one tool?

See [ADR-0002](../decisions/0002-three-component-separation.md) for the full reasoning. In short: Boot Manager, Builder, and Deploy have different operators, different change cadences, and different failure domains, and coupling them would let a failure in one take down the others.

## Who maintains BCS?

BCS is developed at [CIPFP Batoi](https://www.cipfpbatoi.es/), a vocational training centre in Alcoi (Valencian Community, Spain), for the benefit of the wider [LliureX](https://lliurex.net/) community. See [README.md](../../README.md#maintained-by).

## How do I propose a change to the architecture?

Read [CONTRIBUTING.md](../../CONTRIBUTING.md#proposing-an-adr) and write an ADR. Changes to component boundaries, interfaces, or platform scope need one; wording clarifications and typo fixes don't.

## What language should documentation and code be written in?

English, throughout — code, comments, commit messages, and documentation. This is independent of the bilingual (Valencian/Spanish) end-user interface requirement for Boot Manager (`BM-007`), which is about the *product's* UI, not the project's own documentation or source.

## Where do I report a security concern?

Not in a public issue — see [SECURITY.md](../../SECURITY.md#reporting-a-vulnerability) for the private disclosure process.
