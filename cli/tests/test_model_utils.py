from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from bcs.model_utils import reject_non_x_extra


class _ExtensibleForTest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str

    @model_validator(mode="after")
    def _check_extra(self) -> _ExtensibleForTest:
        reject_non_x_extra(self)
        return self


def test_x_prefixed_extra_is_allowed() -> None:
    model = _ExtensibleForTest.model_validate({"name": "a", "x-custom": "ok"})
    assert model.model_extra == {"x-custom": "ok"}


def test_non_x_prefixed_extra_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unexpected property"):
        _ExtensibleForTest.model_validate({"name": "a", "notAllowed": "nope"})


def test_multiple_bad_extras_pluralizes_message() -> None:
    with pytest.raises(ValidationError, match="unexpected properties"):
        _ExtensibleForTest.model_validate({"name": "a", "bad1": 1, "bad2": 2})


def test_no_extra_fields_is_fine() -> None:
    model = _ExtensibleForTest.model_validate({"name": "a"})
    assert model.model_extra == {}
