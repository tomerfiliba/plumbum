"""
Color-related utilities. Feel free to use any color library on
the ``with_color`` statement.

The ``COLOR`` object provides ``BG`` and ``FG`` to access colors,
and attributes like bold and
underlined text. It also provides ``RESET`` to recover the normal font.

With the ``Style`` class, any color can be
directly called or given to a with statement.
"""

from __future__ import print_function
import sys
import os
from contextlib import contextmanager
from plumbum.color.names import color_names_full, color_html_full
from plumbum.color.names import color_names_simple, color_html_simple,  attributes_simple,  from_html
from plumbum.color.names import find_nearest_color, find_nearest_simple_color
from functools import partial

_lower_camel_names = [n.replace('_', '') for n in color_names_full]

class ColorNotFound(AttributeError):
    pass

class BaseColor(object):
    """This class stores the idea of a color, rather than a specific implementation.
    It provides as many different representations as possible, and can be subclassed.
    It is not meant to be mutible. .from_any provides a quick-init shortcut.

    Possible colors::

        blue = ColorBase(0,0,255) # Red, Green, Blue
        green = ColorBase.from_full("green") # Case insensitive name, from large colorset
        red = ColorBase.from_full(1) # Color number
        white = ColorBase.from_html("#FFFFFF") # HTML supported
        yellow = ColorBase.from_simple("red") # Simple colorset


    The attributes are:
        self.fg: Foreground if True, background if not
        self.reset: True it this is a reset color (following atts don't matter if True)
        self.rgb: The red/green/blue tuple for this color
        self.simple: Simple 6 color mode
        self.number: The color number given the mode, closest to rgb if not exact

        """

    use_color = sys.stdout.isatty() and os.name == "posix"
    stdout = sys.stdout

    def __init__(self, r_or_color=None, g=None, b=None, fg=True):
        """This only init's from color values, or tries to load non-simple ones."""

        self.fg = fg
        self.reset = True # Starts as reset color
        self.rgb = (0,0,0)
        self.simple = False

        if r_or_color is not None and None in (g,b):
            try:
                self._from_full(r_or_color)
            except ColorNotFound:
                self._from_html(r_or_color)


        elif None not in (r_or_color, g, b):
            self.rgb = (r_or_color,g,b)
            self._init_number()

    def _init_number(self):
        """Should always be called after filling in r, g, b. Color will not be a reset color anymore."""
        self.number = find_nearest_simple_color(*self.rgb) if self.simple else find_nearest_color(*self.rgb)
        self.reset = False

    @classmethod
    def from_simple(cls, color, fg=True):
        """Creates a color from simple name or color number"""
        self = cls(fg=fg)
        self._from_simple(color)
        return self

    def _from_simple(self, color):
        """Internal loader for from_simple."""
        try:
            color = color.lower()
        except AttributeError:
            pass

        if color == 'reset' or color==9:
            return

        elif color in color_names_simple:
            self.rgb = from_html(color_html_simple[color_names_simple.index(color)])
            self.simple = True

        elif isinstance(color, int) and 0 <= color <= 7:
            self.rgb = from_html(color_html_simple[color])
            self.simple = True

        else:
            raise ColorNotFound("Did not find color: " + repr(color))

        self._init_number()

    @classmethod
    def from_full(cls, color, fg=True):
        """Creates a color from full name or color number"""
        self = cls(fg=fg)
        self._from_full(color)
        return self

    def _from_full(self, color):
        """Creates a color from full name or color number"""
        try:
            color = color.lower()
            color = color.replace(' ','_')
        except AttributeError:
            pass

        if color == 'reset':
            return

        elif color in color_names_full:
            self.rgb = from_html(color_html_full[color_names_full.index(color)])

        elif color in _lower_camel_names:
            self.rgb = from_html(color_html_full[_lower_camel_names.index(color)])

        elif isinstance(color, int) and 0 <= color <= 255:
            self.rgb = from_html(color_html_full[color])

        else:
            raise ColorNotFound("Did not find color: " + repr(color))

        self._init_number()

    @classmethod
    def from_html(cls, color, fg=True):
        """Converts #123456 values to colors."""

        self = cls(fg=fg)
        self._from_html(color)
        return self

    def _from_html(self, color):
        try:
            self.rgb = from_html(color)
        except (TypeError, ValueError):
            raise ColorNotFound("Did not find htmlcode: " + repr(color))

        self._init_number()


    @property
    def r(self):
        return self.rgb[0]

    @property
    def g(self):
        return self.rgb[1]

    @property
    def b(self):
        return self.rgb[2]

    @property
    def name(self):
        if self.reset:
            return 'reset'
        elif self.simple:
            return color_names_simple[self.number]
        else:
            color_names_full[self.number]

    def __repr__(self):
        return "<{0}: {1} {2}>".format(self.__class__.__name__, self.name, self.rgb)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if self.reset:
            return other.reset
        else:
            return self.number == other.number and self.rgb == other.rgb and self.simple == other.simple


class ANSIColor(BaseColor):
    @property
    def ansi_sequence(self):
        if not self.__class__.use_color:
            return ''

        ansi_addition = 30 if self.fg else 40

        if self.reset:
            return '\033[' + str(ansi_addition+9) + 'm'
        elif self.simple:
            return '\033[' + str(self.number+ansi_addition) + 'm'
        else:
            return '\033[' +str(ansi_addition+8) + ';5;' + str(self.number) + 'm'

    def __str__(self):
        return self.ansi_sequence


Color = ANSIColor
