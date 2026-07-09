"""The Network Adapter's pure parser.

Design: ``docs/NETWORK_ADAPTER.md#parser-strategy``, accepted as the
fifth Host Discovery adapter (see
``docs/decisions/0010-efi-adapter-read-only-scope.md`` for the sibling
adapter this module's independence guarantees mirror exactly).

:func:`parse_network_interfaces` is a **pure function**, with the same
independence guarantees already established for every existing Platform
Layer parser:

- It accepts only ``text: str`` - never ``stdout``, for the same
  provenance-independence reason.
- It produces only an immutable Pydantic model
  (:class:`~bcs.platform.adapters.network.models.NetworkInterfaceStatus`).
- It never imports ``subprocess``, ``CommandRunner``,
  ``bcs.platform.execution``, Typer, or Rich, and performs no
  filesystem access - there is no code path by which this module could
  execute anything, print anything, or read anything beyond the string
  it is given.
- It never knows where its input came from - a live tool invocation, a
  fixture file, a value typed at a REPL. Nothing here assumes a
  specific provenance.
- A single text input, not multiple - network interface status comes
  from exactly one tool invocation (``ip -json addr show``).

Parsing approach: JSON-based (``json.loads``), mirroring the Storage
Adapter's parser (``docs/STORAGE_ADAPTER.md#parser-architecture``)
rather than the line-by-line regex approach of the EFI and Secure Boot
parsers, because ``ip -json`` produces structured JSON output by design.
"""

from __future__ import annotations

import json
from typing import Any

from bcs.platform.adapters.network.models import NetworkInterface, NetworkInterfaceStatus

_NULL_MAC = "00:00:00:00:00:00"
_IP_FAMILIES = frozenset({"inet", "inet6"})
_FLAG_LOWER_UP = "LOWER_UP"
_FLAG_UP = "UP"
_FLAG_LOOPBACK = "LOOPBACK"


def parse_network_interfaces(text: str) -> NetworkInterfaceStatus:
    """Parse ``ip -json addr show`` output text into a
    :class:`NetworkInterfaceStatus`.

    Args:
        text: The complete source text to parse, verbatim - today this
            is the stdout of ``ip -json addr show``, but this function
            has no way to know that and does not need to.

    Returns:
        A :class:`NetworkInterfaceStatus` reflecting every interface
        entry the JSON array contained, in the order reported. An empty
        array produces a status with no interfaces (``interfaces=()``) -
        a normal, valid result, not an error.

    Raises:
        ValueError: The input is not valid JSON, is not a JSON array,
            or an entry is missing its ``ifname`` field. The message
            names the 1-based entry index and the specific problem.
    """
    raw = _load_json_array(text)
    interfaces = tuple(_parse_entry(entry, index) for index, entry in enumerate(raw, start=1))
    return NetworkInterfaceStatus(interfaces=interfaces, raw_text=text)


# ---------------------------------------------------------------------------
# per-entry parsing
# ---------------------------------------------------------------------------


def _parse_entry(entry: Any, index: int) -> NetworkInterface:
    if not isinstance(entry, dict):
        msg = f"entry {index}: expected a JSON object, got {type(entry).__name__}"
        raise ValueError(msg)

    name = entry.get("ifname")
    if not isinstance(name, str) or not name:
        msg = f"entry {index}: missing or empty 'ifname'"
        raise ValueError(msg)

    flags = entry.get("flags")
    flags_set = _extract_flags(flags, entry_index=index)

    mac = entry.get("address")
    mac_address = None if mac is None or mac == _NULL_MAC else str(mac)

    ip_addresses = _extract_ip_addresses(entry.get("addr_info"))

    return NetworkInterface(
        name=name,
        mac_address=mac_address,
        ip_addresses=ip_addresses,
        is_up=_FLAG_UP in flags_set and _FLAG_LOWER_UP in flags_set,
        is_loopback=_FLAG_LOOPBACK in flags_set,
    )


def _extract_flags(flags: Any, *, entry_index: int) -> set[str]:
    if not isinstance(flags, list):
        msg = f"entry {entry_index}: 'flags' is not a JSON array"
        raise ValueError(msg)
    result: set[str] = set()
    for item in flags:
        if isinstance(item, str):
            result.add(item)
    return result


def _extract_ip_addresses(addr_info: Any) -> tuple[str, ...]:
    if not isinstance(addr_info, list):
        return ()
    addresses: list[str] = []
    for info in addr_info:
        if isinstance(info, dict) and info.get("family") in _IP_FAMILIES:
            local = info.get("local")
            if isinstance(local, str) and local:
                addresses.append(local)
    return tuple(addresses)


# ---------------------------------------------------------------------------
# top-level JSON loading
# ---------------------------------------------------------------------------


def _load_json_array(text: str) -> list[Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"output is not valid JSON: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(data, list):
        msg = f"expected a JSON array at the top level, got {type(data).__name__}"
        raise ValueError(msg)
    return data


__all__ = ["parse_network_interfaces"]
