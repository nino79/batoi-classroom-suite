"""``bcs validate`` - see ``docs/CLI.md#bcs-validate``.

Runs the pipeline in :mod:`bcs.config.validator` against one or more
ClassroomConfig documents. With no file arguments, resolves exactly one
document per :meth:`~bcs.config.loader.ConfigLoader.resolve_path`.
"""

from __future__ import annotations

from pathlib import Path

from bcs.config.validator import ValidationReport, validate_document
from bcs.context import RuntimeContext
from bcs.errors import ConfigInvalidError
from bcs.output import OutputFormat, print_structured_result


def _print_report_text(runtime: RuntimeContext, report: ValidationReport) -> None:
    for error in report.errors:
        runtime.console.print(f"[red]error[/red] [{error.rule}] {error.path}: {error.message}")
    for warning in report.warnings:
        runtime.console.print(
            f"[yellow]warning[/yellow] [{warning.rule}] {warning.path}: {warning.message}"
        )
    if report.valid and not report.warnings:
        runtime.console.print(f"[green]valid[/green] {report.source}")
    elif report.valid:
        runtime.console.print(f"[yellow]valid with warnings[/yellow] {report.source}")
    else:
        runtime.console.print(f"[red]invalid[/red] {report.source}")


def run_validate(
    runtime: RuntimeContext,
    *,
    files: list[Path] | None = None,
    strict: bool = False,
) -> int:
    """Implement ``bcs validate``. Returns the process exit code."""
    targets = files or [runtime.config_loader.resolve_path()]

    reports = [validate_document(runtime.config_loader, target) for target in targets]

    if runtime.output is OutputFormat.TEXT:
        for report in reports:
            _print_report_text(runtime, report)
    else:
        payload = {
            "results": [{"source": str(report.source), **report.as_dict()} for report in reports]
        }
        print_structured_result(runtime.console, runtime.output, payload)

    all_ok = all(report.is_ok(strict=strict) for report in reports)
    if not all_ok:
        failing = sum(1 for report in reports if not report.is_ok(strict=strict))
        msg = f"{failing} of {len(reports)} document(s) failed validation"
        raise ConfigInvalidError(msg)
    return 0


__all__ = ["run_validate"]
