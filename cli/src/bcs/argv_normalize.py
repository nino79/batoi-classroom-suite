"""Reorder global options so they may appear before *or* after the
subcommand name, per ``docs/CLI.md#invocation-grammar``: ``bcs -v build``
and ``bcs build -v`` must be equivalent.

Click (which Typer builds on) only recognizes a parent group's options
when they appear *before* the subcommand name - anything after belongs
to the subcommand's own parser. Rather than redeclare every global
option on every command, this module rewrites ``argv`` once, up front,
moving any recognized global option token (and its value, if it takes
one) to before the first non-option token, and leaves everything else -
subcommand-specific options, positional arguments, and anything after a
literal ``--`` - untouched and in its original relative order.
"""

from __future__ import annotations

_MIN_GLUED_VERBOSE_LENGTH = 3  # "-vv" is the shortest glued cluster beyond a lone "-v"

#: name -> takes_value, for every global option in docs/CLI.md#global-options.
#: Boolean/eager flags map to False; everything else takes one value.
_GLOBAL_OPTIONS: dict[str, bool] = {
    "--config": True,
    "-c": True,
    "--set": True,
    "--output": True,
    "-o": True,
    "--color": True,
    "--verbose": False,
    "-v": False,
    "--quiet": False,
    "-q": False,
    "--log-level": True,
    "--log-format": True,
    "--log-file": True,
    "--no-input": False,
    "--yes": False,
    "-y": False,
    "--dry-run": False,
    "--timeout": True,
    "--version": False,
    "--help": False,
    "-h": False,
}


def _is_repeated_short_verbose(arg: str) -> bool:
    """Match a glued short-flag cluster like ``-vvv`` (but not ``-v``
    alone, which is handled as a normal flag above)."""
    return len(arg) >= _MIN_GLUED_VERBOSE_LENGTH and arg.startswith("-v") and set(arg[1:]) == {"v"}


def _find_subcommand_index(argv: list[str]) -> int | None:
    """Index of the first token that looks like a subcommand name, or
    ``None`` if ``argv`` ends (or hits ``--``) before one is found.
    """
    for index, arg in enumerate(argv):
        if arg == "--":
            return None
        if not arg.startswith("-") or arg == "-":
            return index
    return None


def _consume_one(after: list[str], index: int) -> tuple[list[str], int, bool]:
    """Classify the token(s) starting at ``after[index]``.

    Returns ``(tokens, next_index, is_global_option)``: ``tokens`` is
    one token, or two if a value-taking global option consumed its
    following argument too.
    """
    arg = after[index]
    name, _, inline_value = arg.partition("=")

    if name in _GLOBAL_OPTIONS:
        takes_value = _GLOBAL_OPTIONS[name]
        if inline_value or not takes_value:
            return [arg], index + 1, True
        if index + 1 < len(after):
            return [arg, after[index + 1]], index + 2, True
        # A value-taking option with nothing following it: leave it in
        # place so Click reports its own clear "missing value" error.
        return [arg], index + 1, False

    if _is_repeated_short_verbose(arg):
        return [arg], index + 1, True

    return [arg], index + 1, False


def normalize_argv(argv: list[str]) -> list[str]:
    """Return ``argv`` with recognized global options hoisted before the
    first subcommand token.

    Everything from a literal ``--`` onward (Click/Unix's
    end-of-options marker) is left exactly as given, including its
    position - options are never hoisted past ``--``.
    """
    subcommand_index = _find_subcommand_index(argv)
    if subcommand_index is None:
        return list(argv)

    before = list(argv[:subcommand_index])
    subcommand = argv[subcommand_index]
    after = argv[subcommand_index + 1 :]

    hoisted: list[str] = []
    remaining: list[str] = []
    index = 0
    while index < len(after):
        if after[index] == "--":
            remaining.extend(after[index:])
            break
        tokens, index, is_global_option = _consume_one(after, index)
        (hoisted if is_global_option else remaining).extend(tokens)

    return [*before, *hoisted, subcommand, *remaining]


__all__ = ["normalize_argv"]
