"""Platform Layer adapters: one package (or module) per external tool,
each a thin translation layer between raw tool output and a typed,
immutable BCS model - see ``docs/PLATFORM_LAYER.md#how-future-adapters-use-it``.

Every adapter is named after the domain it represents, not the tool it
currently wraps - see
``docs/standards/naming-conventions.md#domain-driven-naming``.
"""
