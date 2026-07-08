"""The Filesystem Adapter's pure parser.

Design: ``docs/FILESYSTEM_ADAPTER.md#parser-architecture``. Requires no
ADR - see ``docs/FILESYSTEM_ADAPTER.md#adr-recommendation``.

:func:`parse_filesystem_usage` is a **pure function**, with the same
independence guarantees already established for every sibling
adapter's parser:

- It accepts only ``text: str`` - never ``stdout`` (that would itself
  be a naming leak presupposing the text came from a captured process
  output).
- It produces only immutable Pydantic models
  (:mod:`bcs.platform.adapters.filesystem.models`).
- It never imports ``subprocess``, ``CommandRunner``,
  ``bcs.platform.execution``, Typer, or Rich, and has no dependency on
  the CLI - there is no code path by which this module could execute
  anything or print anything.
- It never knows where its input came from - a live tool invocation, a
  fixture file, a value typed at a REPL.
- A single text input, not three - like the EFI and Secure Boot
  adapters, unlike the Storage Adapter's ``lsblk``/``blkid``/``findmnt``
  composition.

**Exact invocation this parser's contract is built around** (today's
backend, not the parser's own contract)::

    df --output=source,fstype,itotal,iused,iavail,size,used,avail,target -B1 -a

``target`` is placed last because it is the one field that may
legitimately contain internal whitespace (a mount point under a label
with a space in it); ``source`` is placed first because device paths
and pseudo-sources (``tmpfs``, ...) are never whitespace-containing in
practice. Every field between them is guaranteed whitespace-free by
construction.

**Per-line splitting strategy**, addressing the whitespace-in-``target``
problem directly:

1. Split the line on whitespace with ``maxsplit=7``, yielding at most 8
   pieces: the first 7 are ``source``, ``fs_type``, ``itotal``,
   ``iused``, ``iavail``, ``size``, ``used``, each guaranteed to be
   exactly one token; the 8th is ``"avail target"``, still joined,
   with ``target``'s own internal whitespace (if any) fully preserved.
2. Split that remainder once more, with ``maxsplit=1``, into ``avail``
   and ``target``.

**Blank lines** are stripped and skipped unconditionally - they carry
no information to lose.

**Row classification - a fully specified, three-way rule.** For every
non-blank line:

1. **Attempt the split described above.** If the line does not contain
   enough whitespace-separated tokens to produce all 9 positions, it
   cannot be a data row at all - it is rejected as a malformed row,
   ``ValueError`` naming the line number and the offending text
   verbatim. This is deliberately stricter than the "silently skip
   anything unrecognized" default below: a *short* line is the one
   signal that ``df``'s output may have been truncated or corrupted
   mid-stream, a data-loss risk this design does not pass over
   quietly.
2. **If all 9 positions are present, attempt to parse each of the six
   numeric-position fields** (``itotal``/``iused``/``iavail`` as
   either the literal token ``-`` - meaning "not supported for this
   filesystem type," parsed as ``None`` - or a non-negative integer;
   ``size``/``used``/``avail`` as a non-negative integer, no ``-``
   case). **If none of the six parse successfully**, the line does not
   resemble a data row at all - the header row (whatever its exact
   column-label text) or a future banner/warning line - silently
   skipped.
3. **If *all six* numeric-position fields parse successfully**, the
   line is a valid data row - a
   :class:`~bcs.platform.adapters.filesystem.models.FilesystemUsage`
   is built from it.
4. **If *some but not all six* parse successfully**, this is a
   malformed mandatory field - rejected with ``ValueError`` naming the
   specific field, the 1-based line number, and the offending line
   verbatim, exactly matching ``_raise_malformed``'s existing shape in
   ``bcs.platform.adapters.efi.parser``.

Text where every line falls into case 2 (or is blank) - no data row
anywhere - still returns a
:class:`~bcs.platform.adapters.filesystem.models.FilesystemUsageReport`
(``filesystems=()``) from this function - a legitimate parser-level
result, not a parser-level failure. Whether that combination is *also*
an adapter-level "this doesn't look like ``df`` output at all"
condition is a separate, adapter-level judgment - see
``docs/FILESYSTEM_ADAPTER.md#error-mapping``.

**No cross-field validation exists in the parser itself.** It never
deduplicates, reorders, or drops an entry for any reason other than
the row-classification rule above - see
``docs/FILESYSTEM_ADAPTER.md#domain-models`` for why
``FilesystemUsageReport`` performs no duplicate-``target`` check
either. ``raw_stderr`` is always left at its model default (``""``) by
this function - it never sees ``stderr`` at all; attaching the real
value is ``adapter.py``'s job.
"""

from __future__ import annotations

import re
from typing import NoReturn

from bcs.platform.adapters.filesystem.models import FilesystemUsage, FilesystemUsageReport

_NON_NEGATIVE_INT_RE = re.compile(r"^\d+$")

# `df`'s own "not supported for this filesystem type" placeholder for
# inode-position fields - not a secret, despite the token's shape.
_INODE_FIELD_ABSENT = "-"

# The leading split (source/fs_type/itotal/iused/iavail/size/used +
# remainder) must yield exactly this many pieces; the remainder split
# (avail + target) must yield exactly this many.
_EXPECTED_LEADING_FIELDS = 8
_EXPECTED_REMAINDER_FIELDS = 2


def parse_filesystem_usage(text: str) -> FilesystemUsageReport:
    """Parse ``text`` into a :class:`FilesystemUsageReport`.

    Args:
        text: The complete source text to parse, verbatim - today this
            is ``df --output=...``'s stdout, but this function has no
            way to know that and does not need to.

    Returns:
        A :class:`FilesystemUsageReport` with one
        :class:`FilesystemUsage` per recognized data row, in the order
        they appeared. ``filesystems=()`` if no data row was found - a
        normal, valid result, not an error. ``raw_stderr`` is always
        ``""`` (its model default); this function never sees
        ``stderr``.

    Raises:
        ValueError: A non-blank line had fewer than 9
            whitespace-separated positions (a malformed row), or had
            all 9 positions but some, not all, of its six
            numeric-position fields failed to parse (a malformed
            field). The message quotes the 1-based line number and the
            offending line verbatim.
    """
    filesystems: list[FilesystemUsage] = []

    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        parts = stripped.split(None, 7)
        if len(parts) < _EXPECTED_LEADING_FIELDS:
            _raise_malformed_row(line=line, number=number)
        source, fs_type, itotal_raw, iused_raw, iavail_raw, size_raw, used_raw, remainder = parts

        remainder_parts = remainder.split(None, 1)
        if len(remainder_parts) < _EXPECTED_REMAINDER_FIELDS:
            _raise_malformed_row(line=line, number=number)
        avail_raw, target = remainder_parts

        itotal_ok, itotal = _try_parse_inode_field(itotal_raw)
        iused_ok, iused = _try_parse_inode_field(iused_raw)
        iavail_ok, iavail = _try_parse_inode_field(iavail_raw)
        size_ok, size = _try_parse_byte_field(size_raw)
        used_ok, used = _try_parse_byte_field(used_raw)
        avail_ok, avail = _try_parse_byte_field(avail_raw)

        fields = (
            ("itotal", itotal_ok),
            ("iused", iused_ok),
            ("iavail", iavail_ok),
            ("size", size_ok),
            ("used", used_ok),
            ("avail", avail_ok),
        )
        successes = sum(1 for _, ok in fields if ok)

        if successes == 0:
            # Header row or a future banner/warning line: ignored, per
            # this module's permissive design.
            continue

        if successes < len(fields):
            failed_field = next(field_name for field_name, ok in fields if not ok)
            _raise_malformed_field(field_name=failed_field, line=line, number=number)

        filesystems.append(
            FilesystemUsage(
                source=source,
                target=target,
                fs_type=fs_type,
                size_bytes=size,
                used_bytes=used,
                available_bytes=avail,
                inodes_total=itotal,
                inodes_used=iused,
                inodes_available=iavail,
                raw_line=line,
            )
        )

    return FilesystemUsageReport(filesystems=tuple(filesystems), raw_text=text)


def _try_parse_inode_field(token: str) -> tuple[bool, int | None]:
    """Parse one inode-position field: ``-`` means None, per df's own convention."""
    if token == _INODE_FIELD_ABSENT:
        return True, None
    if _NON_NEGATIVE_INT_RE.fullmatch(token):
        return True, int(token)
    return False, None


def _try_parse_byte_field(token: str) -> tuple[bool, int]:
    """Parse one byte-position field: always a non-negative integer, never '-'."""
    if _NON_NEGATIVE_INT_RE.fullmatch(token):
        return True, int(token)
    return False, 0


def _raise_malformed_row(*, line: str, number: int) -> NoReturn:
    msg = f"malformed row (line {number}): {line!r}"
    raise ValueError(msg)


def _raise_malformed_field(*, field_name: str, line: str, number: int) -> NoReturn:
    msg = f"malformed {field_name} line (line {number}): {line!r}"
    raise ValueError(msg)


__all__ = ["parse_filesystem_usage"]
