"""The Secure Boot Adapter's pure parser.

Design: ``docs/SECURE_BOOT_ADAPTER.md#parser-strategy``. Requires no
ADR - see ``docs/SECURE_BOOT_ADAPTER.md#adr-recommendation``.

:func:`parse_secure_boot_status` is a **pure function**, with the same
independence guarantees already established for the EFI Adapter's
parser (``docs/EFI_ADAPTER.md#parser-architecture``) and applied here
for the third time:

- It accepts only ``text: str`` - never ``stdout`` (that would itself
  be a naming leak presupposing the text came from a captured process
  output).
- It produces only an immutable Pydantic model
  (:class:`~bcs.platform.adapters.secureboot.models.SecureBootStatus`).
- It never imports ``subprocess``, ``CommandRunner``,
  ``bcs.platform.execution``, Typer, or Rich, and has no dependency on
  the CLI - there is no code path by which this module could execute
  anything or print anything.
- It never knows where its input came from - a live tool invocation, a
  fixture file, a value typed at a REPL. Nothing here assumes a
  specific provenance.
- A single text input, not three (unlike the Storage Adapter's
  ``lsblk``/``blkid``/``findmnt`` composition) - Secure Boot state
  comes from exactly one tool invocation.

Parsing philosophy: line by line, permissive by default, identical in
spirit to the EFI Adapter's own rule and now a settled project
convention rather than a one-off. A line matching no recognized
pattern at all is silently ignored - a future ``mokutil`` version
adding an unrelated line, or a distribution-specific banner, does not
break parsing; text with *no* recognized lines at all still returns a
``SecureBootStatus`` (``state=UNKNOWN``, ``setup_mode=None``), a
legitimate result, not a failure. A line starting with the literal
prefix ``SecureBoot `` or ``SetupMode ``, whose value is neither
``enabled`` nor ``disabled``, is a **malformed mandatory field** -
rejected with a ``ValueError`` that quotes the offending line and its
1-based position, exactly matching ``_raise_malformed``'s existing
shape in ``bcs.platform.adapters.efi.parser``.

This function performs no cross-field validation - unlike
``FirmwareBootConfiguration``'s duplicate-``boot_number`` check,
``SecureBootStatus`` has no collection field for a uniqueness
constraint to apply to.
"""

from __future__ import annotations

import re
from typing import NoReturn

from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus

_SECURE_BOOT_PREFIX_RE = re.compile(r"^SecureBoot\s")
_SECURE_BOOT_VALUE_RE = re.compile(r"^SecureBoot\s+(enabled|disabled)$")
_SETUP_MODE_PREFIX_RE = re.compile(r"^SetupMode\s")
_SETUP_MODE_VALUE_RE = re.compile(r"^SetupMode\s+(enabled|disabled)$")


def parse_secure_boot_status(text: str) -> SecureBootStatus:
    """Parse ``text`` into a :class:`SecureBootStatus`.

    Args:
        text: The complete source text to parse, verbatim - today this
            is ``mokutil --sb-state``'s stdout, but this function has
            no way to know that and does not need to.

    Returns:
        A :class:`SecureBootStatus` reflecting every recognized line
        in ``text``. ``state`` is ``UNKNOWN`` and ``setup_mode`` is
        ``None`` if their respective line was never found - a normal,
        valid result, not an error; a genuinely unparseable-looking
        input is an adapter-level concern
        (``docs/SECURE_BOOT_ADAPTER.md#error-mapping``), not this
        function's.

    Raises:
        ValueError: A line matched the literal prefix ``SecureBoot ``
            or ``SetupMode `` but its value was neither ``enabled``
            nor ``disabled``. The message quotes the 1-based line
            number and the offending line verbatim.
    """
    state = SecureBootState.UNKNOWN
    setup_mode: bool | None = None

    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        if _SECURE_BOOT_PREFIX_RE.match(stripped):
            match = _SECURE_BOOT_VALUE_RE.match(stripped)
            if match is None:
                _raise_malformed(line=line, number=number, field_name="SecureBoot")
            state = (
                SecureBootState.ENABLED if match.group(1) == "enabled" else SecureBootState.DISABLED
            )
            continue

        if _SETUP_MODE_PREFIX_RE.match(stripped):
            match = _SETUP_MODE_VALUE_RE.match(stripped)
            if match is None:
                _raise_malformed(line=line, number=number, field_name="SetupMode")
            setup_mode = match.group(1) == "enabled"
            continue

        # Unrecognized line: ignored, per this module's permissive design.

    return SecureBootStatus(state=state, setup_mode=setup_mode, raw_text=text)


def _raise_malformed(*, line: str, number: int, field_name: str) -> NoReturn:
    msg = f"malformed {field_name} line (line {number}): {line!r}"
    raise ValueError(msg)


__all__ = ["parse_secure_boot_status"]
