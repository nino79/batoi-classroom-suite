# Security Policy

Batoi Classroom Suite (BCS) manages the boot process and disk contents of fleets of physical classroom machines. Even during its documentation-only phase, we treat the design with the security posture the eventual implementation will require: a flaw in Boot Manager's fallback logic, Builder's image provenance, or Deploy's network imaging path could affect every machine in a classroom at once.

## Supported Versions

BCS has not yet reached a `1.0.0` release. During the pre-1.0 phase, only the latest state of the `main` branch is supported with security fixes.

| Version | Supported |
|---|---|
| `main` (unreleased) | ✅ |
| `< 0.1.0` | ❌ |

This table will be expanded with concrete supported version ranges once `1.0.0` ships, following [Semantic Versioning](https://semver.org/).

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately using [GitHub Security Advisories](https://github.com/nino79/batoi-classroom-suite/security/advisories/new) for this repository. This creates a private discussion with maintainers before any public disclosure.

When reporting, please include:

- A description of the vulnerability and its potential impact.
- Which component is affected (Boot Manager, Builder, Deploy, or the documentation/tooling itself).
- Steps to reproduce, or the reasoning behind a design-level concern if no code exists yet.
- Any suggested remediation, if you have one.

### What to expect

- **Acknowledgement:** we aim to acknowledge new reports within 5 business days.
- **Assessment:** we will confirm whether the report is in scope and its severity, and discuss a remediation plan with you.
- **Disclosure:** we follow coordinated disclosure — we ask that you not publicly disclose the issue until a fix or mitigation is available, or 90 days have passed, whichever comes first. We will credit reporters (unless anonymity is requested) in the advisory and `CHANGELOG.md`.

## Security-Relevant Design Areas

Given BCS's role, the following areas are treated as security-sensitive throughout the architecture (see [ARCHITECTURE.md](ARCHITECTURE.md) and [SPECIFICATION.md](SPECIFICATION.md)) and warrant particular scrutiny in reports and reviews:

- **Boot integrity.** Boot Manager's interaction with UEFI Secure Boot and its fallback behavior (SPEC `BM-005`) — a compromised or misconfigured boot path affects every session on that machine.
- **Image provenance.** Builder's checksumming and build provenance (SPEC `BLD-006`) — an unverified or tampered golden image would be distributed to an entire classroom by Deploy.
- **Network deployment trust.** Deploy's PXE and multicast imaging path (SPEC `DEP-002`) — classroom LANs must be able to trust that imaging traffic originates from the legitimate Deploy server, not a rogue PXE/multicast source.
- **Secrets handling.** No golden image may embed long-lived shared credentials (SPEC `NFR-003`); any secrets required at deploy time must be injected at deployment time.

## Scope

This policy covers the BCS repository content and, once implementation begins, the Boot Manager, Builder, and Deploy components. It does not cover LliureX itself, Ubuntu, Clonezilla, or other upstream projects BCS depends on — please report vulnerabilities in those projects to their respective maintainers.
