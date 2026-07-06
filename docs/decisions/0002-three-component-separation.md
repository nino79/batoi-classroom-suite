# ADR-0002: Three-Component Separation (Boot Manager / Builder / Deploy)

**Status:** Accepted

## Context

A classroom deployment platform could plausibly be built as a single, monolithic tool that handles image building, network deployment, and boot-time behaviour all together — and in fact, many ad hoc school-IT solutions look exactly like that: a pile of scripts that grew organically to cover "everything about getting a classroom working."

BCS instead needs to support three distinct operational realities that don't share a lifecycle:

- **Building** a golden image is a periodic, deliberate, often offline activity (a new school year, a curriculum change, a security patch) performed by whoever maintains the "what should this classroom run" definition.
- **Deploying** that image is a scheduled, network-bound, classroom-scale operation performed by on-site technical staff during a maintenance window.
- **Booting** happens on every single machine, every single session, unattended, and must work even when nobody is around to intervene.

These three activities have different operators, different failure modes, different change cadences, and — critically — a failure in one must not be able to take down the others. A bug in an image-build script should not be able to brick a machine's boot process; a boot-menu misconfiguration should not require rebuilding the golden image to fix.

## Decision

We will structure BCS as three independently versioned components — Boot Manager, Builder, Deploy — each with a single responsibility, communicating only through well-defined artifacts and interfaces (a golden image artifact, a deployed disk layout, a maintenance request), never through shared code or shared runtime state. See [ARCHITECTURE.md §4](../../ARCHITECTURE.md#4-component-boundaries) for the interface contracts this implies.

### Alternatives Considered

- **Single monolithic tool.** Rejected: conflates three different operators and change cadences into one codebase and one release cycle, and makes it easy to accidentally couple boot-time logic to build-time assumptions (or vice versa).
- **Two components (build+deploy combined, boot manager separate).** Rejected: Builder and Deploy have genuinely different scaling concerns (Builder is a batch, offline process; Deploy is a live, network-bound, time-boxed operation) and different failure domains — a slow build should never be able to stall a live classroom deployment session.

## Consequences

- Each component can be developed, tested, and reasoned about independently, per its own specification in `docs/specifications/`.
- Integration only happens through the documented artifact/interface contracts — any temptation to have one component reach into another's internals is a signal to revisit this ADR or write an interface-changing ADR of its own, not to just do it.
- This does add coordination overhead for changes that genuinely span components (e.g., the Boot Manager ↔ Deploy maintenance-request interface) — those are explicitly called out as open, jointly-owned questions in the relevant architecture documents rather than being decided unilaterally by one component's design.
