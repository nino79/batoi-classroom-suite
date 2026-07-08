# Secure Boot Fixtures — Reserved

Reserved for captured output for the **Secure Boot Adapter**
(`bcs.platform.adapters.secureboot`, see
[docs/SECURE_BOOT_ADAPTER.md](../../../../docs/SECURE_BOOT_ADAPTER.md),
`Accepted`), which closes a known placeholder gap in today's Host Inventory
(`FirmwareInfo.secure_boot` currently reports `unknown` on UEFI systems;
see [docs/HOST_INVENTORY.md § Open
Questions](../../../../docs/HOST_INVENTORY.md#open-questions--explicitly-deferred)).
The adapter's design is accepted and wraps `mokutil --sb-state`; its domain
models, parser, and error hierarchy are implemented, but `adapter.py` (the
only module that would actually invoke `mokutil`) does not exist yet, so no
real capture is possible from this codebase today.

**Deliberately empty.** The required command line, scenarios, and an
inventory table will be added once `adapter.py` is implemented and a real
capture is possible. General collection, locale, anonymization, naming, and
placeholder rules already apply and are in the
[corpus root README](../README.md).
