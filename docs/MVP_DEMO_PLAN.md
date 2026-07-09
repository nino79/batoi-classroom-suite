# MVP Demo Plan — Presenting `bcs` on Ubuntu 24.04

**Duration:** ~20-25 minutes total
**Audience:** Technical stakeholders (sysadmins, developers)
**Goal:** Demonstrate that the `bcs` CLI framework, Host Inventory, Platform Layer, and Host Discovery are real, tested, installable software.

## Segments

### 1. Context (2 min)

> "BCS is a deployment platform for LliureX classrooms. We're currently in Phase 0 — Foundation. The three main components (Boot Manager, Builder, Deploy) are still in planning, but the CLI framework and its Host Discovery subsystem are real, tested Python code. Let me show you what exists today."

### 2. Fresh Install (3 min)

```bash
# On a fresh Ubuntu 24.04 VM:
sudo apt update && sudo apt install -y git python3-venv
git clone https://github.com/nino79/batoi-classroom-suite.git
cd batoi-classroom-suite/cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Key talking points:**
- Two dependencies: `git` and `python3-venv` (both from Ubuntu repos)
- Editable install — source is visible and debuggable
- 1026 passing tests, 96% coverage

### 3. Basic Commands (3 min)

```bash
bcs --help        # full command tree
bcs version       # version, commit, build info
```

**Key talking points:**
- 11 commands in the tree
- 4 implemented (version, doctor, inventory, validate)
- 7 stubs (will return in Phases 1-3)
- Git-style plugin dispatch for third-party extensions

### 4. Config Validation (3 min)

```bash
bcs validate ../config/examples/default.yaml
bcs validate --help
```

**Key talking points:**
- Validates against `config/schema.yaml` (JSON Schema)
- Pydantic models mirror the schema exactly
- Semantic checks beyond what JSON Schema can express
- `--strict` mode promotes warnings to errors

### 5. Host Inventory (5 min)

```bash
bcs inventory                         # text output
bcs inventory --output json | jq .    # structured data
```

**Key talking points:**
- 10 fact sections: identity, firmware, OS, CPU, memory, storage, network, ESP, USB storage, tooling
- Immutable, versioned schema (`bcs-inventory/v1alpha1`)
- `bcs inventory --output json` is the canonical serialisation
- Same facts used by `bcs doctor`, so they never disagree
- Future: consumed by Builder and Deploy when those exist

### 6. Host Doctor (3 min)

```bash
bcs doctor
bcs doctor --check firmware
```

**Key talking points:**
- Pass/fail/warn per check (modeled on `flutter doctor`)
- Evaluates against Host Inventory facts (not a second probe)
- Missing Clonezilla is expected on a non-LliureX machine
- `--fix` attempts safe remediations; `--strict` treats warnings as failures

### 7. Architecture Overview (2 min)

```bash
# Show the adapter layer is real:
python3 -c "import bcs.platform.adapters.efi; print('EFI adapter:', bcs.platform.adapters.efi.__all__)"
python3 -c "import bcs.platform.adapters.storage; print('Storage adapter:', bcs.platform.adapters.storage.__all__)"
```

**Key talking points:**
- Platform Layer: `CommandRunner` abstraction over `subprocess`
- 4 fully-implemented adapters (EFI, Storage, Secure Boot, Filesystem)
- Network adapter implemented but not yet wired in
- Host Discovery Orchestrator coordinates all adapters into one snapshot
- No CLI command passes the orchestrator through yet — that's the next engineering step

### 8. Stubs & Scope (2 min)

```bash
bcs build --help
bcs deploy --help
bcs config --help
```

**Key talking points:**
- Each stub reports "not implemented in this phase" and exits non-zero
- This is by design — no Boot Manager, Builder, or Deploy logic exists yet
- Their designs are documented and ready in `docs/`

### 9. Q&A (remaining time)

## Troubleshooting During Demo

| If This Happens | Say This |
|---|---|
| `bcs: command not found` | "Let me check the venv is active" — `source .venv/bin/activate` |
| `pip install` fails | "Let me check network connectivity" — verify NAT networking |
| `bcs doctor` shows all FAIL | "This VM may not have EFI enabled — let me verify the VM settings" |
| `bcs inventory` has empty fields | "That's expected for a VM — some facts need real hardware to populate" |
| `bcs validate` errors | "Let me check the config file path" — verify working directory is `cli/` |
