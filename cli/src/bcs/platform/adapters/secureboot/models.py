"""Immutable domain models for the Secure Boot Adapter.

Design: ``docs/SECURE_BOOT_ADAPTER.md#domain-models``. This design
requires no ADR (see ``docs/SECURE_BOOT_ADAPTER.md#adr-recommendation``)
- every architectural mechanism it uses was already decided by
``docs/decisions/0010-efi-adapter-read-only-scope.md``.

This module contains **only the models** - no parsing logic, no
``subprocess``, no :class:`~bcs.platform.execution.CommandRunner`, no
adapter, no CLI integration. ``SecureBootStatus`` represents an
**observed fact** about the firmware's current Secure Boot state,
exactly as reported by the underlying tool; it does not decide whether
Secure Boot *should* be enabled, and does not compare its observation
against ``spec.security.secureBoot.mode`` - that comparison is
``bcs doctor``'s responsibility, per
``docs/SECURE_BOOT_ADAPTER.md#scope-guarantee``. Validation in this
module checks only intrinsic model consistency - it has no concept of
what a "correct" state is.

Naming is domain-driven, not tied to the current backend tool
(``mokutil``) - see
``docs/standards/naming-conventions.md#domain-driven-naming``:
``SecureBootStatus``, not ``SecureBootConfiguration`` (which would
collide with the existing, policy-flavored
``spec.security.secureBoot.mode`` - see
``docs/SECURE_BOOT_ADAPTER.md#naming-rationale`` for the full
rationale).

``SecureBootState`` is an **independently defined** enum, not imported
from :mod:`bcs.inventory.models` - reusing that one would create a
dependency from ``bcs.platform`` (a lower layer) up into
``bcs.inventory`` (a higher layer), the inverse of every Platform Layer
document's stated dependency direction. It deliberately shares the
same name and the same four values, in the same order, as
:class:`bcs.inventory.models.SecureBootState` - see
``docs/SECURE_BOOT_ADAPTER.md#naming-rationale``.

Field naming mirrors the rest of BCS's models: Python attributes are
``snake_case``, JSON output is ``camelCase`` (``by_alias=True``), and
``populate_by_name=True`` lets callers construct instances with either
spelling. The model is frozen, matching every other model in
``bcs.platform``/``bcs.inventory`` - a point-in-time record, never a
live view.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SecureBootState(StrEnum):
    """Firmware Secure Boot state, as observed by this adapter.

    Independently defined from, but value-for-value identical to,
    :class:`bcs.inventory.models.SecureBootState` - see this module's
    own docstring for why the two are never shared by import.
    """

    ENABLED = "enabled"
    DISABLED = "disabled"
    #: Not a UEFI system, or the firmware has no Secure Boot support at all.
    UNSUPPORTED = "unsupported"
    #: A UEFI system whose Secure Boot state could not be determined.
    UNKNOWN = "unknown"


class SecureBootStatus(BaseModel):
    """The firmware's currently reported Secure Boot state and UEFI
    Setup Mode, as observed.

    Deliberately does **not** carry its own ``schemaVersion`` - like
    ``CommandResult`` and ``FirmwareBootConfiguration``, this model is
    never the top-level payload of a ``bcs`` command's own output; it
    is always embedded inside something else's result, so versioning
    is that container's responsibility. See
    ``docs/SECURE_BOOT_ADAPTER.md#domain-models`` for the authoritative
    field-by-field reference this class implements exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    state: SecureBootState = Field(
        description=(
            "The firmware's currently reported Secure Boot state, as "
            "observed. UNKNOWN if the source text reported neither "
            "'enabled' nor 'disabled' in a recognizable form - never guessed."
        )
    )
    setup_mode: bool | None = Field(
        alias="setupMode",
        default=None,
        description=(
            "Whether the platform is currently in UEFI Setup Mode. None if "
            "the source text didn't report it - expected on some tool "
            "versions, not an error."
        ),
    )
    raw_text: str = Field(
        alias="rawText",
        description=(
            "The complete, unparsed source text, verbatim. Named raw_text, "
            "not raw_output, precisely because this model has no concept of "
            "'output' - it does not know whether its data came from a "
            "process, a file, or anywhere else."
        ),
    )


__all__ = ["SecureBootState", "SecureBootStatus"]
