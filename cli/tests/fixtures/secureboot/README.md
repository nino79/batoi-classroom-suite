# Secure Boot Fixtures — Reserved

Reserved for captured output supporting future Secure Boot state detection
(`PLAT-004`) — a known placeholder gap in today's Host Inventory
(`FirmwareInfo.secure_boot` currently reports `unknown` on UEFI systems;
see [docs/HOST_INVENTORY.md § Open
Questions](../../../../docs/HOST_INVENTORY.md#open-questions--explicitly-deferred)).
No adapter for this domain is designed yet, and no tool has been chosen
(`mokutil`, direct `efivarfs` reads, or something else — that choice belongs
to the future design, not to this directory).

**Deliberately empty.** The required command line, scenarios, and an
inventory table will be added when that adapter's design is written and
accepted. General collection, locale, anonymization, naming, and
placeholder rules already apply and are in the
[corpus root README](../README.md).
