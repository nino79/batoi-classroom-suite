"""Tests for the pure Network Adapter parser.

Per the fixture corpus's own placeholder rules
(``tests/fixtures/README.md``), the real corpus
(``tests/fixtures/network/``) currently holds only zero-byte
placeholders - no real captured output exists yet. These tests therefore
build a *temporary*, ``tmp_path``-rooted corpus (mirroring
``tests/fixtures/``'s own layout) and load every scenario through
``fixture_utils.py``, exactly as real captures will be loaded once they
exist - never by passing an inline string straight to the parser. The
real corpus is never written to.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bcs.platform.adapters.network.parser import parse_network_interfaces
from fixture_utils import load_fixture

_VALID_FIXTURES: dict[str, str] = {
    "ip_test_ubuntu-24.04_ethernet-up.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", '
        '"addr_info": [{"family": "inet", "local": "10.0.2.15", "prefixlen": 24}]}]'
    ),
    "ip_test_ubuntu-24.04_ethernet-down.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST"], '
        '"address": "52:54:00:12:34:56", "addr_info": []}]'
    ),
    "ip_test_ubuntu-24.04_multi-interface.txt": (
        '[{"ifname": "lo", "flags": ["LOOPBACK", "UP", "LOWER_UP"], '
        '"address": "00:00:00:00:00:00", '
        '"addr_info": [{"family": "inet", "local": "127.0.0.1", "prefixlen": 8}]}, '
        '{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", '
        '"addr_info": [{"family": "inet", "local": "10.0.2.15", "prefixlen": 24}]}]'
    ),
    "ip_test_ubuntu-24.04_ipv6-only.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", '
        '"addr_info": [{"family": "inet6", "local": "fe80::5054:ff:fe12:3456", '
        '"prefixlen": 64, "scope": "link"}]}]'
    ),
    "ip_test_ubuntu-24.04_no-address.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", "addr_info": []}]'
    ),
    "ip_test_ubuntu-24.04_empty.txt": "[]",
    "ip_test_ubuntu-24.04_null-mac.txt": (
        '[{"ifname": "lo", "flags": ["LOOPBACK", "UP", "LOWER_UP"], '
        '"address": "00:00:00:00:00:00", "addr_info": []}]'
    ),
    "ip_test_ubuntu-24.04_no-mac.txt": (
        '[{"ifname": "lo", "flags": ["LOOPBACK", "UP", "LOWER_UP"], "addr_info": []}]'
    ),
    "ip_test_ubuntu-24.04_no-addr-info.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56"}]'
    ),
    "ip_test_ubuntu-24.04_addr-info-not-array.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", "addr_info": null}]'
    ),
    "ip_test_ubuntu-24.04_non-ip-addr-info.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", '
        '"addr_info": [{"family": "packet", "ifindex": 2}, '
        '{"family": "inet", "local": "10.0.2.15", "prefixlen": 24}]}]'
    ),
    "ip_test_ubuntu-24.04_unknown-fields.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", '
        '"addr_info": [{"family": "inet", "local": "10.0.2.15", "prefixlen": 24}], '
        '"bogus_field": "ignored", "another_unknown": 42}]'
    ),
    "ip_test_ubuntu-24.04_non_string_flag.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", 42, "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", "addr_info": []}]'
    ),
    "ip_test_ubuntu-24.04_addr_info_missing_local.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
        '"address": "52:54:00:12:34:56", '
        '"addr_info": [{"family": "inet", "prefixlen": 24}]}]'
    ),
    "ip_test_ubuntu-24.04_not-up-or-lower-up.txt": (
        '[{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST"], '
        '"address": "52:54:00:12:34:56", "addr_info": []}]'
    ),
}

_INVALID_FIXTURES: dict[str, str] = {
    "ip_test_ubuntu-24.04_not-json.txt": "not json",
    "ip_test_ubuntu-24.04_not-array.txt": '{"ifname": "eth0"}',
    "ip_test_ubuntu-24.04_entry-not-object.txt": '["eth0"]',
    "ip_test_ubuntu-24.04_missing-ifname.txt": (
        '[{"flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], "addr_info": []}]'
    ),
    "ip_test_ubuntu-24.04_empty-ifname.txt": (
        '[{"ifname": "", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], "addr_info": []}]'
    ),
    "ip_test_ubuntu-24.04_flags-not-array.txt": (
        '[{"ifname": "eth0", "flags": "not-a-list", "addr_info": []}]'
    ),
}


@pytest.fixture
def synthetic_corpus(tmp_path: Path) -> Path:
    """A temporary corpus, mirroring tests/fixtures/'s own layout, holding
    synthetic-but-realistic scenarios for parser correctness only. Never
    writes to the real corpus.
    """
    valid_dir = tmp_path / "network" / "generic"
    invalid_dir = tmp_path / "network" / "generic-invalid"
    valid_dir.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)
    for name, content in _VALID_FIXTURES.items():
        (valid_dir / name).write_text(content, encoding="utf-8")
    for name, content in _INVALID_FIXTURES.items():
        (invalid_dir / name).write_text(content, encoding="utf-8")
    return tmp_path


def _load(root: Path, name: str, *, invalid: bool = False) -> str:
    category = "generic-invalid" if invalid else "generic"
    return load_fixture("network", category, name, root=root)


# ---------------------------------------------------------------------------
# well-formed scenarios
# ---------------------------------------------------------------------------


def test_single_ethernet_up(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_ethernet-up.txt")
    status = parse_network_interfaces(text)

    assert status.raw_text == text
    assert len(status.interfaces) == 1
    eth0 = status.interfaces[0]
    assert eth0.name == "eth0"
    assert eth0.mac_address == "52:54:00:12:34:56"
    assert eth0.ip_addresses == ("10.0.2.15",)
    assert eth0.is_up is True
    assert eth0.is_loopback is False


def test_ethernet_down(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_ethernet-down.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    eth0 = status.interfaces[0]
    assert eth0.name == "eth0"
    assert eth0.is_up is False
    assert eth0.is_loopback is False


def test_multi_interface(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_multi-interface.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 2
    lo = status.interfaces[0]
    assert lo.name == "lo"
    assert lo.mac_address is None
    assert lo.ip_addresses == ("127.0.0.1",)
    assert lo.is_up is True
    assert lo.is_loopback is True

    eth0 = status.interfaces[1]
    assert eth0.name == "eth0"
    assert eth0.mac_address == "52:54:00:12:34:56"
    assert eth0.ip_addresses == ("10.0.2.15",)
    assert eth0.is_up is True
    assert eth0.is_loopback is False


def test_ipv6_only(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_ipv6-only.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    eth0 = status.interfaces[0]
    assert eth0.name == "eth0"
    assert eth0.ip_addresses == ("fe80::5054:ff:fe12:3456",)
    assert eth0.is_up is True


def test_no_addresses(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_no-address.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    assert status.interfaces[0].ip_addresses == ()


def test_empty_json_array(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_empty.txt")
    status = parse_network_interfaces(text)

    assert status.interfaces == ()
    assert status.raw_text == "[]"


def test_null_mac_normalised_to_none(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_null-mac.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    assert status.interfaces[0].mac_address is None


def test_absent_mac_defaults_to_none(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_no-mac.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    assert status.interfaces[0].mac_address is None


def test_absent_addr_info_yields_empty_ip_addresses(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_no-addr-info.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    assert status.interfaces[0].ip_addresses == ()


def test_non_array_addr_info_treated_as_absent(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_addr-info-not-array.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    assert status.interfaces[0].ip_addresses == ()


def test_non_ip_addr_info_families_are_skipped(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_non-ip-addr-info.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    # Only the 'inet' entry's local is collected; 'packet' is skipped
    assert status.interfaces[0].ip_addresses == ("10.0.2.15",)


def test_unknown_fields_are_silently_ignored(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_unknown-fields.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    assert status.interfaces[0].name == "eth0"


def test_non_string_flag_silently_ignored(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_non_string_flag.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    # Non-string flag (42) is ignored, but string flags are still parsed
    assert status.interfaces[0].is_up is True


def test_addr_info_missing_local_skipped(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_addr_info_missing_local.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    # The 'inet' entry without 'local' is skipped, so ip_addresses stays empty
    assert status.interfaces[0].ip_addresses == ()


def test_not_up_or_lower_up(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_not-up-or-lower-up.txt")
    status = parse_network_interfaces(text)

    assert len(status.interfaces) == 1
    assert status.interfaces[0].is_up is False
    assert status.interfaces[0].is_loopback is False


@pytest.mark.parametrize("name", sorted(_VALID_FIXTURES))
def test_every_valid_fixture_parses_without_error(synthetic_corpus: Path, name: str) -> None:
    text = _load(synthetic_corpus, name)
    status = parse_network_interfaces(text)
    assert status.raw_text == text


# ---------------------------------------------------------------------------
# malformed inputs - rejected with ValueError
# ---------------------------------------------------------------------------


def test_invalid_json_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_not-json.txt", invalid=True)
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_network_interfaces(text)


def test_non_array_top_level_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_not-array.txt", invalid=True)
    with pytest.raises(ValueError, match="expected a JSON array"):
        parse_network_interfaces(text)


def test_entry_not_an_object_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_entry-not-object.txt", invalid=True)
    with pytest.raises(ValueError, match="entry 1: expected a JSON object"):
        parse_network_interfaces(text)


def test_missing_ifname_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_missing-ifname.txt", invalid=True)
    with pytest.raises(ValueError, match=r"entry 1: missing or empty 'ifname'"):
        parse_network_interfaces(text)


def test_empty_ifname_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_empty-ifname.txt", invalid=True)
    with pytest.raises(ValueError, match=r"entry 1: missing or empty 'ifname'"):
        parse_network_interfaces(text)


def test_flags_not_a_list_is_rejected(synthetic_corpus: Path) -> None:
    text = _load(synthetic_corpus, "ip_test_ubuntu-24.04_flags-not-array.txt", invalid=True)
    with pytest.raises(ValueError, match=r"entry 1: 'flags' is not a JSON array"):
        parse_network_interfaces(text)


@pytest.mark.parametrize("name", sorted(_INVALID_FIXTURES))
def test_every_invalid_fixture_is_rejected(synthetic_corpus: Path, name: str) -> None:
    text = _load(synthetic_corpus, name, invalid=True)
    with pytest.raises(ValueError):
        parse_network_interfaces(text)


# ---------------------------------------------------------------------------
# inline edge cases not covered by synthetic corpus
# ---------------------------------------------------------------------------


def test_empty_string_is_rejected() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_network_interfaces("")


# ---------------------------------------------------------------------------
# purity / independence
# ---------------------------------------------------------------------------


def test_parser_module_imports_nothing_but_stdlib_and_its_own_models() -> None:
    import ast

    import bcs.platform.adapters.network.parser as parser_module

    source = Path(parser_module.__file__).read_text(encoding="utf-8")
    imported_modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden = {
        "subprocess",
        "typer",
        "rich",
        "click",
        "bcs.platform.execution",
        "bcs.context",
        "bcs.app",
        "bcs.inventory",
        "bcs.platform.adapters.efi",
        "bcs.platform.adapters.storage",
        "bcs.platform.adapters.network.errors",
    }
    assert not imported_modules & forbidden
    assert imported_modules == {
        "__future__",
        "json",
        "typing",
        "bcs.platform.adapters.network.models",
    }
