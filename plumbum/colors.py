"""
This module imitates a real module, providing standard syntax
like from `plumbum.colors` and from `plumbum.colors.bg` to work alongside
all the standard syntax for colors.
"""

import sys
import os
from types import ModuleType

from plumbum.colorlib import ANSIStyle, StyleFactory

class ColorModuleType(ModuleType, StyleFactory):
    
    def __init__(self, name, style):
        ModuleType.__init__(self, name)
        StyleFactory.__init__(self, style)
        self.__path__ = os.path.abspath(os.path.dirname(__file__))

mymodule = ColorModuleType(__name__, ANSIStyle)

# Oddly, the order here matters for Python2, but not Python3
sys.modules[__name__ + '.fg'] = mymodule.fg
sys.modules[__name__ + '.bg'] = mymodule.bg
sys.modules[__name__] = mymodule

