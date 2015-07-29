"""
This module imitates a real module, providing standard syntax
like from `plumbum.colors` and from `plumbum.colors.bg` to work alongside
all the standard syntax for colors.
"""

import sys
import os

from plumbum.colorlib import ansicolors


# Oddly, the order here matters for Python2, but not Python3
sys.modules[__name__ + '.fg'] = ansicolors.fg
sys.modules[__name__ + '.bg'] = ansicolors.bg
sys.modules[__name__] = ansicolors

