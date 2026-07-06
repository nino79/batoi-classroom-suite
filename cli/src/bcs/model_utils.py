"""Shared Pydantic model building blocks used across ``bcs`` subsystems.

Both the ClassroomConfig models (``bcs.config.models``) and the Host
Inventory models (``bcs.inventory.models``) need the same
"``x-``-prefixed extra keys only" extensibility rule (see
``docs/CONFIGURATION.md#extensibility-model``); this module is the one
place that rule is implemented, so the two domains can't drift apart on
what counts as a valid extension key.
"""

from __future__ import annotations

from pydantic import BaseModel


def reject_non_x_extra(model: BaseModel) -> BaseModel:
    """Raise ``ValueError`` if ``model`` has any extra field not prefixed
    ``x-``. Intended for use inside an ``@model_validator(mode="after")``
    on a model whose ``model_config`` sets ``extra="allow"``.
    """
    extra = model.model_extra or {}
    bad = [key for key in extra if not key.startswith("x-")]
    if bad:
        msg = f"unexpected propert{'y' if len(bad) == 1 else 'ies'}: {', '.join(sorted(bad))}"
        raise ValueError(msg)
    return model


__all__ = ["reject_non_x_extra"]
