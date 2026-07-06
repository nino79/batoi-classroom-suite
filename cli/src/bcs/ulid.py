"""Minimal ULID generation, stdlib-only.

``docs/CLI.md#logging--verbosity`` specifies a ULID as the invocation ID
shared by every log line and session report for one ``bcs`` run. Rather
than add a dependency beyond the four named in the implementation brief
(Typer, Rich, Pydantic, PyYAML), this implements the ULID spec
(https://github.com/ulid/spec) directly: a 48-bit millisecond timestamp
followed by 80 bits of randomness, Crockford Base32 encoded to 26
characters.
"""

from __future__ import annotations

import os
import time

_CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TIMESTAMP_LEN = 10
_RANDOMNESS_LEN = 16
_RANDOMNESS_BYTES = 10


def _encode(value: int, length: int) -> str:
    chars = [""] * length
    for i in range(length - 1, -1, -1):
        chars[i] = _CROCKFORD_ALPHABET[value & 0x1F]
        value >>= 5
    return "".join(chars)


def new_ulid() -> str:
    """Return a new, time-sortable ULID string."""
    timestamp_ms = time.time_ns() // 1_000_000
    timestamp_part = _encode(timestamp_ms, _TIMESTAMP_LEN)
    randomness = int.from_bytes(os.urandom(_RANDOMNESS_BYTES), byteorder="big")
    randomness_part = _encode(randomness, _RANDOMNESS_LEN)
    return timestamp_part + randomness_part


__all__ = ["new_ulid"]
