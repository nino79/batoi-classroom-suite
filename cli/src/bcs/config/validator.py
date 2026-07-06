"""Semantic (cross-field) validation, per
``docs/CLI.md#validation-flow``.

These are the checks JSON Schema (``config/schema.yaml``) cannot express
on its own. Each has a stable rule ID, matching the table in
``docs/CLI.md``. Structural validation (types/required/enum/const/
pattern) is Pydantic's job, in :mod:`bcs.config.loader`; this module
only runs once a document has already passed that stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bcs.config.loader import ConfigLoader, parse_classroom_config
from bcs.config.models import ClassroomConfig
from bcs.errors import ConfigInvalidError


@dataclass(frozen=True)
class Finding:
    """One validation error or warning."""

    rule: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"rule": self.rule, "path": self.path, "message": self.message}


@dataclass
class ValidationReport:
    """The full outcome of validating one document."""

    source: Path
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def is_ok(self, *, strict: bool) -> bool:
        """Whether this report should be treated as a pass.

        Warnings alone are a pass unless ``--strict`` escalates them,
        matching ``bcs validate``/``bcs doctor``'s shared ``--strict``
        semantics in ``docs/CLI.md``.
        """
        if self.errors:
            return False
        return not (strict and self.warnings)

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "errors": [e.as_dict() for e in self.errors],
            "warnings": [w.as_dict() for w in self.warnings],
        }


def run_semantic_checks(config: ClassroomConfig) -> tuple[list[Finding], list[Finding]]:
    """Run every semantic rule and return ``(errors, warnings)``."""
    errors: list[Finding] = []
    warnings: list[Finding] = []

    supported_locales = set(config.spec.localization.supported_locales)
    for index, entry in enumerate(config.spec.boot_manager.menu.entries):
        for locale in entry.label:
            if locale not in supported_locales:
                errors.append(
                    Finding(
                        rule="label-locale-coverage",
                        path=f"spec.bootManager.menu.entries.{index}.label.{locale}",
                        message=(
                            f"locale {locale!r} is not listed in spec.localization.supportedLocales"
                        ),
                    )
                )

    entry_ids = {entry.id for entry in config.spec.boot_manager.menu.entries}
    default_entry = config.spec.boot_manager.menu.default_entry
    if default_entry not in entry_ids:
        errors.append(
            Finding(
                rule="default-entry-exists",
                path="spec.bootManager.menu.defaultEntry",
                message=f"references unknown entry id {default_entry!r}",
            )
        )

    builder_checksum = config.spec.builder.provenance.checksum_algorithm
    deploy_checksum = config.spec.deploy.verification.checksum_algorithm
    if builder_checksum != deploy_checksum:
        warnings.append(
            Finding(
                rule="checksum-algorithm-match",
                path="spec.deploy.verification.checksumAlgorithm",
                message=(
                    f"{deploy_checksum!r} does not match "
                    f"spec.builder.provenance.checksumAlgorithm ({builder_checksum!r})"
                ),
            )
        )

    addressing = config.spec.network.addressing
    if addressing.mode == "static" and not addressing.static_assignments:
        warnings.append(
            Finding(
                rule="static-assignments-present",
                path="spec.network.addressing.staticAssignments",
                message="addressing.mode is 'static' but staticAssignments is empty",
            )
        )

    return errors, warnings


def validate_document(loader: ConfigLoader, source: Path) -> ValidationReport:
    """Run the full pipeline (schema + semantic) for one document.

    Unlike :meth:`ConfigLoader.load`, this never raises on an invalid
    document - the whole point of ``bcs validate`` is to report every
    problem at once, not abort at the first one.
    """
    report = ValidationReport(source=source)
    try:
        document = loader.load_raw(source)
        config = parse_classroom_config(document, source=source)
    except ConfigInvalidError as exc:
        messages = exc.errors or [exc.message]
        report.errors.extend(
            Finding(rule="schema", path="$", message=message) for message in messages
        )
        return report

    errors, warnings = run_semantic_checks(config)
    report.errors.extend(errors)
    report.warnings.extend(warnings)
    return report


__all__ = ["Finding", "ValidationReport", "run_semantic_checks", "validate_document"]
