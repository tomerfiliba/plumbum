"""
This module imitates a real module, providing standard syntax
like from `plumbum.colors` and from `plumbum.colors.bg` to work alongside
all the standard syntax for colors.
"""

from __future__ import print_function
import sys
import os
import atexit

from plumbum.colorlib import ansicolors, main
_reset = ansicolors.reset.now
if __name__ == '__main__':
    main()
else:  # Don't register an exit if this is called using -m!
    atexit.register(_reset)

# Oddly, the order here matters for Python2, but not Python3
sys.modules[__name__ + '.fg'] = ansicolors.fg
sys.modules[__name__ + '.bg'] = ansicolors.bg
sys.modules[__name__] = ansicolors
