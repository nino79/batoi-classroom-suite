"""Immutable domain models for the EFI Adapter.

Design: ``docs/EFI_ADAPTER.md#pydantic-models``, accepted per
``docs/decisions/0010-efi-adapter-read-only-scope.md``.

This module contains **only the models** - no parsing logic, no
``subprocess``, no :class:`~bcs.platform.execution.CommandRunner`, no
adapter, no CLI integration. Both models represent facts about the
*firmware's* boot configuration; neither has any notion of how that
data was obtained (a live tool invocation, a fixture file, anything
else) - that independence is deliberate and is the same property the
future pure parser is designed to have (see
``docs/EFI_ADAPTER.md#parser-architecture``).

Naming is domain-driven, not tied to the current backend tool
(``efibootmgr``) - see
``docs/standards/naming-conventions.md#domain-driven-naming``:
``FirmwareBootConfiguration``, not ``EfiBootConfiguration``, and not
``BootConfiguration`` (which would collide with Boot Manager's own,
unrelated ``spec.bootManager.menu`` concept - see
``docs/EFI_ADAPTER.md#pydantic-models`` for the full rationale).

Field naming mirrors the rest of BCS's models: Python attributes are
``snake_case``, JSON output is ``camelCase`` (``by_alias=True``), and
``populate_by_name=True`` lets callers construct instances with either
spelling. Both models are frozen, matching every other model in
``bcs.platform``/``bcs.inventory`` - a point-in-time record, never a
live view.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: The four-hexadecimal-digit format of a UEFI boot number (e.g. "0000",
#: as in "Boot0000"), per docs/EFI_ADAPTER.md's own field description.
_BOOT_NUMBER_PATTERN = re.compile(r"^[0-9A-Fa-f]{4}$")


def _validate_boot_number(value: str, *, field_name: str) -> str:
    """Shared format check for every boot-number-shaped field."""
    if not _BOOT_NUMBER_PATTERN.fullmatch(value):
        msg = f"{field_name} must be a four-hexadecimal-digit boot number, got {value!r}"
        raise ValueError(msg)
    return value


class BootEntry(BaseModel):
    """One UEFI boot entry (a ``Boot####`` NVRAM variable), as reported
    by the firmware.

    See ``docs/EFI_ADAPTER.md#pydantic-models`` for the authoritative
    field-by-field reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    boot_number: str = Field(
        alias="bootNumber",
        description=(
            "The four-hex-digit boot ID, e.g. '0000' - kept as a string (not "
            "parsed as an integer), since it is always referenced and displayed "
            "as a fixed-width hex code, never arithmetically."
        ),
    )
    label: str = Field(
        description="The human-readable label, e.g. 'ubuntu', 'Windows Boot Manager'."
    )
    active: bool = Field(
        description="Whether this entry is active/enabled in the firmware's boot process."
    )
    device_path: str = Field(
        alias="devicePath",
        description=(
            "The UEFI device path text as reported (e.g. "
            "'HD(1,GPT,...)/File(\\\\EFI\\\\ubuntu\\\\shimx64.efi)'), kept opaque and "
            "verbatim. Empty string if the entry had no path segment."
        ),
    )
    raw_line: str = Field(
        alias="rawLine",
        description=(
            "The entry's complete original source line, verbatim - the "
            "per-entry equivalent of FirmwareBootConfiguration.raw_text, so "
            "nothing is ever lost even if a field above was left unstructured."
        ),
    )

    @field_validator("boot_number")
    @classmethod
    def _check_boot_number_format(cls, value: str) -> str:
        return _validate_boot_number(value, field_name="boot_number")


class FirmwareBootConfiguration(BaseModel):
    """The firmware's complete UEFI boot configuration, as reported.

    Deliberately does **not** carry its own ``schemaVersion`` - like
    ``CommandResult``, this model is never the top-level payload of a
    ``bcs`` command's own output; it is always embedded inside
    something else's result, so versioning is that container's
    responsibility. See ``docs/EFI_ADAPTER.md#pydantic-models`` for the
    authoritative field-by-field reference this class implements
    exactly, and ``docs/EFI_ADAPTER.md#open-questions`` for the
    still-undecided question of what that container actually is.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    current_boot_number: str | None = Field(
        alias="currentBootNumber",
        default=None,
        description=(
            "The boot entry the firmware actually used for this boot. None if "
            "absent from the source text (defensive; not expected on a real "
            "UEFI system, but never fabricated)."
        ),
    )
    timeout_seconds: int | None = Field(
        alias="timeoutSeconds",
        default=None,
        ge=0,
        description=(
            "The firmware's boot-menu timeout, in seconds. None if absent - "
            "meaning 'firmware default,' not 'zero.'"
        ),
    )
    boot_order: tuple[str, ...] = Field(
        alias="bootOrder",
        default_factory=tuple,
        description=(
            "The ordered list of boot numbers the firmware will try. Empty "
            "tuple if absent from the source text."
        ),
    )
    boot_next: str | None = Field(
        alias="bootNext",
        default=None,
        description="A one-time next-boot override, present only when set.",
    )
    entries: tuple[BootEntry, ...] = Field(
        default_factory=tuple,
        description=(
            "Every boot entry found, in the order the source text presented "
            "them - not reordered to match boot_order. A consumer wanting "
            "'the entry currently first in the boot order' cross-references "
            "boot_order[0] against entries[].boot_number itself; this model "
            "does not duplicate that lookup as a convenience field."
        ),
    )
    raw_text: str = Field(
        alias="rawText",
        description=(
            "The complete, unparsed source text, verbatim. Named raw_text, not "
            "raw_output, precisely because this model has no concept of "
            "'output' - it does not know whether its data came from a process, "
            "a file, or anywhere else."
        ),
    )

    @field_validator("current_boot_number", "boot_next")
    @classmethod
    def _check_optional_boot_number_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_boot_number(value, field_name="current_boot_number/boot_next")

    @field_validator("boot_order")
    @classmethod
    def _check_boot_order_format(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for item in value:
            _validate_boot_number(item, field_name="boot_order entry")
        return value

    @model_validator(mode="after")
    def _check_entries_have_unique_boot_numbers(self) -> FirmwareBootConfiguration:
        numbers = [entry.boot_number for entry in self.entries]
        if len(numbers) != len(set(numbers)):
            msg = "entries must not contain duplicate boot_number values"
            raise ValueError(msg)
        return self


__all__ = ["BootEntry", "FirmwareBootConfiguration"]
