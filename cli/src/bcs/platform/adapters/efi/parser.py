"""The EFI Adapter's pure parser.

Design: ``docs/EFI_ADAPTER.md#parser-architecture``, accepted per
``docs/decisions/0010-efi-adapter-read-only-scope.md``.

:func:`parse_firmware_boot_configuration` is a **pure function**, and
its independence from the execution layer is a load-bearing design
property, not an incidental detail:

- It accepts only ``text: str`` - never ``stdout`` (that would itself
  be a naming leak presupposing the text came from a captured process
  output).
- It produces only immutable Pydantic models
  (:mod:`bcs.platform.adapters.efi.models`).
- It never imports ``subprocess``, ``CommandRunner``,
  ``bcs.platform.execution``, Typer, or Rich, and has no dependency on
  the CLI - there is no code path by which this module could execute
  anything or print anything.
- It never knows where its input came from - a live tool invocation, a
  fixture file, a value typed at a REPL. Nothing here assumes a
  specific provenance.

Parsing philosophy: line by line, permissive by default. A line that
does not match any recognized pattern at all is silently ignored - a
future tool version may add fields this parser doesn't yet know about,
and ``FirmwareBootConfiguration.raw_text``/``BootEntry.raw_line``
preserve everything verbatim regardless, so nothing is actually lost.
A line that *does* match a recognized prefix (``BootCurrent:``,
``Timeout:``, ``BootOrder:``, ``BootNext:``, a ``Boot####`` entry) but
whose value fails the format that prefix implies is a different
matter - a **malformed mandatory field**, rejected with a ``ValueError``
that quotes the offending line and its position, chained from any
underlying cause. This is what keeps the parser both robust against
harmless format drift and strict about data that is actually broken.
"""

from __future__ import annotations

import re
from typing import NoReturn

from bcs.platform.adapters.efi.models import BootEntry, FirmwareBootConfiguration

_HEX4 = re.compile(r"^[0-9A-Fa-f]{4}$")

_BOOT_CURRENT_RE = re.compile(r"^BootCurrent:\s*(.*)$")
_TIMEOUT_PREFIX_RE = re.compile(r"^Timeout:")
_TIMEOUT_VALUE_RE = re.compile(r"^Timeout:\s*(\d+)")
_BOOT_ORDER_RE = re.compile(r"^BootOrder:\s*(.*)$")
_BOOT_NEXT_RE = re.compile(r"^BootNext:\s*(.*)$")
_BOOT_ENTRY_RE = re.compile(r"^Boot([0-9A-Fa-f]{4})(\*?)\s+(.*)$")


def parse_firmware_boot_configuration(text: str) -> FirmwareBootConfiguration:
    """Parse ``text`` into a :class:`FirmwareBootConfiguration`.

    Args:
        text: The complete source text to parse, verbatim - today this
            is ``efibootmgr -v``'s stdout, but this function has no
            way to know that and does not need to.

    Returns:
        A :class:`FirmwareBootConfiguration` reflecting every
        recognized line in ``text``. Fields with no corresponding line
        take their model defaults (``None`` for scalars, an empty
        tuple for collections) - this is a normal, valid result, not
        an error; a genuinely unparseable-looking input is an
        adapter-level concern (see
        ``docs/EFI_ADAPTER.md#error-mapping``), not this function's.

    Raises:
        ValueError: A line matched a recognized prefix
            (``BootCurrent:``, ``Timeout:``, ``BootOrder:``,
            ``BootNext:``) but its value did not match the format that
            prefix requires. The message quotes the 1-based line
            number and the offending line verbatim.
        pydantic.ValidationError: The assembled data violates a model
            invariant this function cannot check line-by-line - e.g.
            two entries sharing the same ``boot_number`` (see
            :meth:`FirmwareBootConfiguration._check_entries_have_unique_boot_numbers`).
    """
    current_boot_number: str | None = None
    timeout_seconds: int | None = None
    boot_order: tuple[str, ...] = ()
    boot_next: str | None = None
    entries: list[BootEntry] = []

    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        match = _BOOT_CURRENT_RE.match(stripped)
        if match:
            current_boot_number = _parse_optional_hex4(
                match.group(1), line=line, number=number, field_name="BootCurrent"
            )
            continue

        if _TIMEOUT_PREFIX_RE.match(stripped):
            timeout_match = _TIMEOUT_VALUE_RE.match(stripped)
            if timeout_match is None:
                _raise_malformed(line=line, number=number, field_name="Timeout")
            timeout_seconds = int(timeout_match.group(1))
            continue

        match = _BOOT_ORDER_RE.match(stripped)
        if match:
            boot_order = _parse_boot_order(match.group(1), line=line, number=number)
            continue

        match = _BOOT_NEXT_RE.match(stripped)
        if match:
            boot_next = _parse_optional_hex4(
                match.group(1), line=line, number=number, field_name="BootNext"
            )
            continue

        match = _BOOT_ENTRY_RE.match(stripped)
        if match:
            boot_number, marker, rest = match.groups()
            label, _tab, device_path = rest.partition("\t")
            entries.append(
                BootEntry(
                    boot_number=boot_number,
                    label=label,
                    active=(marker == "*"),
                    device_path=device_path,
                    raw_line=line,
                )
            )
            continue

        # Unrecognized line: ignored, per this module's permissive design.

    return FirmwareBootConfiguration(
        current_boot_number=current_boot_number,
        timeout_seconds=timeout_seconds,
        boot_order=boot_order,
        boot_next=boot_next,
        entries=tuple(entries),
        raw_text=text,
    )


def _parse_optional_hex4(value: str, *, line: str, number: int, field_name: str) -> str | None:
    """Parse an optional four-hex-digit value from a recognized field's line.

    An empty value (the prefix matched but nothing followed it) means
    "absent," per this field's own model description - not malformed.
    """
    value = value.strip()
    if not value:
        return None
    if not _HEX4.fullmatch(value):
        _raise_malformed(line=line, number=number, field_name=field_name)
    return value


def _parse_boot_order(value: str, *, line: str, number: int) -> tuple[str, ...]:
    """Parse a comma-separated ``BootOrder:`` value into boot numbers.

    An empty value means "empty boot order," per this field's own
    model description - not malformed.
    """
    value = value.strip()
    if not value:
        return ()
    parts = tuple(part.strip() for part in value.split(","))
    for part in parts:
        if not _HEX4.fullmatch(part):
            _raise_malformed(line=line, number=number, field_name="BootOrder")
    return parts


def _raise_malformed(*, line: str, number: int, field_name: str) -> NoReturn:
    msg = f"malformed {field_name} line (line {number}): {line!r}"
    raise ValueError(msg)


__all__ = ["parse_firmware_boot_configuration"]
