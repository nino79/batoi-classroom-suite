from __future__ import annotations

import re
import time

from bcs.ulid import new_ulid

_ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def test_ulid_shape() -> None:
    value = new_ulid()
    assert len(value) == 26
    assert _ULID_PATTERN.match(value), value


def test_ulid_uniqueness() -> None:
    values = {new_ulid() for _ in range(100)}
    assert len(values) == 100


def test_ulid_is_lexicographically_sortable_by_time() -> None:
    first = new_ulid()
    time.sleep(0.005)
    second = new_ulid()
    assert first < second
