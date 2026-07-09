# bcs (Python implementation)

This is the implementation of `bcs`, the Batoi Classroom Suite command-line interface. The design this code implements is documented in [`../docs/CLI.md`](../docs/CLI.md); the decision to implement it in Python (superseding the Bash-based plan in [ADR-0004](../docs/decisions/0004-bash-as-primary-implementation-language.md)/[ADR-0006](../docs/decisions/0006-bcs-unified-cli-architecture.md)) is recorded in [ADR-0007](../docs/decisions/0007-python-for-the-bcs-cli.md).

This implementation phase covers **only the CLI framework**: global options, logging, configuration loading/validation, the Host Inventory subsystem, and the `version`, `doctor`, `inventory`, and `validate` commands (with placeholder check logic where noted). `build`, `install`, `deploy`, `backup`, `restore`, `update`, and `config` are registered so `bcs --help` reflects the full command surface, but each is a stub that reports it isn't implemented yet — no Boot Manager, Builder, or Deploy logic exists in this package.

## Requirements

- Python 3.12
- [Typer](https://typer.tiangolo.com/), [Rich](https://rich.readthedocs.io/), [Pydantic](https://docs.pydantic.dev/) v2, [PyYAML](https://pyyaml.org/) — the only runtime dependencies, per this phase's brief.

## Development Setup

On a clean Ubuntu 24.04 machine, the `venv` module is a separate package —
without it, `python3.12 -m venv` fails with `ensurepip is not available`:

```bash
sudo apt update && sudo apt install -y python3.12-venv git
```

Then, from a clone of this repository:

```bash
cd cli
python3.12 -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

Never `pip install` outside a venv on Ubuntu 24.04 — the system Python is
externally managed (PEP 668) and will refuse the install.

## Running

```bash
bcs --help
bcs version
bcs doctor
bcs inventory --output json
bcs validate ../config/examples/default.yaml
```

## Quality Gates

All four are configured in [`pyproject.toml`](pyproject.toml) and enforced in CI ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):

```bash
ruff check .
ruff format --check .
mypy
pytest
```

## Layout

```
cli/
├── pyproject.toml        # packaging + ruff/mypy/pytest configuration
├── src/bcs/
│   ├── app.py             # root Typer app: global options, plugin dispatch, command registration
│   ├── __main__.py         # process entry point (bcs console script)
│   ├── context.py          # RuntimeContext - the run's dependency-injection container
│   ├── exit_codes.py       # the shared ExitCode scheme (docs/CLI.md#exit-codes)
│   ├── errors.py           # BcsError hierarchy, one subclass per exit code
│   ├── logging_setup.py    # verbosity levels, text/JSON log formatting
│   ├── color.py             # NO_COLOR/TTY-aware Rich console construction
│   ├── output.py           # schemaVersion-tagged JSON/YAML result printing
│   ├── plugins.py          # bcs-<name> PATH discovery and dispatch
│   ├── ulid.py              # stdlib-only ULID generator (invocation IDs)
│   ├── model_utils.py       # shared Pydantic extensibility helper (x- extra-key rule)
│   ├── config/              # ClassroomConfig loading, Pydantic models, validation
│   ├── inventory/            # Host Inventory subsystem: models, collectors, service
│   ├── platform/             # Platform Layer: CommandRunner, CommandResult, adapters/
│   └── commands/            # one module per command
└── tests/                  # pytest suite, one file per module/command
    ├── fixtures/               # captured-tool-output corpus for adapter tests (see its README)
    └── fixture_utils.py        # shared helpers for loading that corpus
```

See [`../docs/repository-organization.md`](../docs/repository-organization.md) for how this directory fits into the rest of the repository.
