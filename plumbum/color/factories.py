"""
Color-related factories. They produce Styles.

"""

from __future__ import print_function
import sys
import os
from functools import partial
from contextlib import contextmanager
from plumbum.color.names import color_names_simple

__all__ = ['ColorFactory', 'StyleFactory']


class ColorFactory(object):

    """This creates color names given fg = True/False. It usually will
    be called as part of a StyleFactory."""

    def __init__(self, fg, style):
        self._fg = fg
        self._style = style
        self.RESET = style.from_color(style.color_class(fg=fg))

        # Adding the color name shortcuts for forground colors
        for item in color_names_simple:
            setattr(self, item.upper(), style.from_color(style.color_class.from_simple(item, fg=fg)))


    def full(self, name):
        """Gets the style for a color, using standard name procedure: either full
        color name, html code, or number."""
# TODO: add html to int conversion, so that all HTML colors work
        return self._style.from_color(self._style.color_class(name, fg=self._fg))

    def simple(self, name):
        """Return the extended color scheme color for a value or name."""
        return self._style.from_color(self._style.color_class.from_simple(name, fg=self._fg))

    def rgb(self, r, g, b):
        """Return the extended color scheme color for a value."""
        return self._style.from_color(self._style.color_class(r, g, b, fg=self._fg))


    def __getitem__(self, val):
        """Shortcut to provide way to access extended colors."""
        return self.full(val)

    def __call__(self, val):
        """Shortcut to provide way to access simple colors."""
        return self.simple(val)

    def __iter__(self):
        """Iterates through all colors in extended colorset."""
        return (self.full(i) for i in range(256))

    def __neg__(self):
        """Allows clearing a color"""
        return self.RESET

    def __rsub__(self, other):
        return other + (-self)

    def __enter__(self):
        """This will reset the color on leaving the with statement."""
        return self

    def __exit__(self, type, value, traceback):
        """This resets a FG/BG color or all styles,
        due to different definition of RESET for the
        factories."""

        self._style.stdout.write(str(self.RESET))
        return False

    def __repr__(self):
        return "<{0}>".format(self.__class__.__name__)

class StyleFactory(ColorFactory):

    """Factory for styles. Holds font styles, FG and BG objects representing colors, and
    imitates the FG ColorFactory to a large degree."""

    def __init__(self, style):
        super(StyleFactory,self).__init__(True, style)

        self.FG = ColorFactory(True, style)
        self.BG = ColorFactory(False, style)

        self.DO_NOTHING = style()
        self.RESET = style(reset=True)

        for item in style.attribute_names:
            setattr(self, item.upper(), style(attributes={item:True}))
            setattr(self, "NON_"+item.upper(), style(attributes={item:False}))

