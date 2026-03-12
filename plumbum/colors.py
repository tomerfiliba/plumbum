"""
This module imitates a real module, providing standard syntax
like from `plumbum.colors` and from `plumbum.colors.bg` to work alongside
all the standard syntax for colors.
"""

from __future__ import annotations

import atexit
import sys

from plumbum.colorlib import ansicolors, main

_reset = ansicolors.reset.now


def ensure_colors_reset() -> None:
    """
    Call this to ensure colors are reset when the program exits. Might add an
    extra blank line.
    """
    atexit.register(_reset)


# Keep module-like metadata on the proxy object for tools that introspect it.
ansicolors.__name__ = __name__  # type: ignore[attr-defined]

sys.modules[__name__ + ".fg"] = ansicolors.fg  # type: ignore[assignment]
sys.modules[__name__ + ".bg"] = ansicolors.bg  # type: ignore[assignment]
sys.modules[__name__] = ansicolors  # type: ignore[assignment]


if __name__ == "__main__":
    main()
