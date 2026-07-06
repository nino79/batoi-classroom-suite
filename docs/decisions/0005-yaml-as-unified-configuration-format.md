# ADR-0005: YAML as the Unified Configuration Format

**Status:** Accepted

## Context

`BLD-001` requires Builder to accept "a declarative recipe/manifest describing package sets, configuration, and branding," but left the actual format as an open question (see the open questions in [docs/architecture/builder.md](../architecture/builder.md)). Deploy separately needs configuration (network transport, session sizing) and Boot Manager needs configuration (menu entries, branding, Secure Boot posture). Left unresolved, this invites three independently-invented formats — one per component — which would contradict the "one concept, one field" discipline the rest of this documentation set tries to hold itself to, and would give a future contributor three different config languages to learn instead of one.

An unrelated but reinforcing signal: an architecture review of this repository (see `REVIEW.md`) flagged both the undefined recipe format and the "recipe" vs. "manifest" naming ambiguity in `docs/glossary.md` as concrete gaps. This ADR resolves both at once by defining one configuration format for the whole platform.

### Options Considered

- **YAML, with a Kubernetes-style `apiVersion`/`kind`/`metadata`/`spec` envelope.** Human-readable, supports comments (unlike JSON), ubiquitous in infrastructure tooling this project's operators already encounter (Ansible, Docker Compose, Kubernetes itself), and the envelope gives the schema a built-in versioning and multi-document-type story without inventing one. Downside: YAML's flexible typing (implicit booleans, the Norway Problem) requires a schema to pin down, which this project provides via `config/schema.yaml`.
- **TOML.** Cleaner unambiguous typing than YAML, popular in newer tooling (Cargo, some Python packaging). Rejected: weaker support for deeply nested structures (this configuration has meaningfully nested sections — `bootManager.menu.entries[].label`), and far less familiar to the sysadmin/classroom-IT audience this project serves than YAML, which they already encounter via Ansible-adjacent tooling in the wider Linux school-IT ecosystem.
- **JSON.** Unambiguous and has first-class JSON Schema support. Rejected as the *authoring* format: no comments, and worse ergonomics for a document humans are expected to write and review directly (as opposed to a machine-generated config). JSON Schema is still used *underneath* — `config/schema.yaml` is JSON Schema expressed in YAML syntax, giving both authoring ergonomics and a rigorous, tooling-friendly contract.
- **HCL (HashiCorp Configuration Language).** Good ergonomics for infrastructure-as-code, but adds a dependency on HCL tooling with no other presence in this project's stack (no Terraform/Vault usage anywhere in BCS), and is less familiar to the target operator audience than YAML.
- **A custom DSL or INI-style format.** Rejected outright: inventing a bespoke configuration language is exactly the kind of unforced technical debt a 10-year-maintained project should avoid — every contributor would need to learn a format that exists nowhere else, with no existing editor/tooling support.
- **Three separate formats, one per component.** Rejected: directly reintroduces the "recipe/manifest" ambiguity this ADR exists to close, and violates `ARCHITECTURE.md`'s "artifacts over shared state" principle only partially — the components would still need to agree on shared concepts (locales, machine identity) across three schemas instead of one.

## Decision

BCS uses a **single YAML configuration document per classroom**, with a Kubernetes-inspired envelope (`apiVersion`, `kind: ClassroomConfig`, `metadata`, `spec`), validated against a JSON Schema (Draft-07) contract at `config/schema.yaml`. This document is the authoritative source for Boot Manager's menu/branding, Builder's build recipe (`BLD-001`), and Deploy's session/network parameters. Full field-by-field documentation is in [docs/CONFIGURATION.md](../CONFIGURATION.md).

The terms "recipe" and "manifest," used interchangeably in earlier documents, are retired in favor of "configuration" (the whole document) and, informally, "recipe" for the `spec.builder`/`spec.packages` subset Builder consumes.

Extensibility is handled through three distinct, purpose-built mechanisms rather than one generic escape hatch — see [docs/CONFIGURATION.md §Extensibility Model](../CONFIGURATION.md#extensibility-model):

1. `apiVersion` for schema-breaking evolution (new versions, not silent breaking changes to `v1alpha1`).
2. `spec.extensions` for structured fields that haven't graduated into the formal schema.
3. `x-`-prefixed keys (Docker Compose convention) for ad hoc tooling metadata.

## Consequences

- Boot Manager, Builder, and Deploy share one configuration language and one document per classroom, closing the open format question left by `BLD-001` and removing a documentation ambiguity flagged in `REVIEW.md`.
- Builder becomes the single component that parses this document at runtime; Boot Manager and Deploy consume only what Builder/the document hands them directly (see [docs/CONFIGURATION.md §How the File Is Consumed](../CONFIGURATION.md#how-the-file-is-consumed)) — this preserves the "artifacts over shared state" principle from `ARCHITECTURE.md` rather than having all three components independently parse and trust the same live file.
- A schema-validation step becomes a required part of Builder's implementation (and ideally CI), which is new scope relative to a world with no defined format — this is treated as worthwhile scope, not overhead, since an invalid configuration reaching a real classroom is a worse outcome than a build failing early.
- Multi-classroom/multi-centre configuration composition (sharing a base config across many rooms) is explicitly **not** solved by this ADR — see the open questions in [docs/CONFIGURATION.md](../CONFIGURATION.md#open-questions) — and is deferred rather than speculatively designed now, consistent with the proportionality concern raised in `REVIEW.md §7`.
- Future breaking changes to the configuration format must ship as a new `apiVersion` with a documented deprecation window, not a silent redefinition of `v1alpha1` — this constrains future contributors in a way that's deliberate, not accidental.
