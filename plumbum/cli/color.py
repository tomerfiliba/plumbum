"""
Color-related utilities. Feel free to use any color library on
the ``with_color`` statement.

The ``COLOR`` object provides ``BG`` and ``FG`` to access colors,
and attributes like bold and
underlined text. It also provides ``RESET`` to recover the normal font.

With the ``Style`` string subclass being used, any color can be
directly called or given to a with statement.
"""

from __future__ import with_statement, print_function
import sys
import os
from contextlib import contextmanager

# This can be manually forced using plumbum.cli.color.USE_COLOR = True
USE_COLOR = sys.stdout.isatty() and os.name == "posix"
STDOUT = sys.stdout


class Style(str):
    """This class allows the color change strings to be called directly
    to write them to stdout, and can be called in a with statement."""


    def negate(self):
        """This negates the effect of the current color"""
        return self.__class__(self._remove() if USE_COLOR else '')

    def now(self, wrap_this=None):
        STDOUT.write(self.wrap(wrap_this))

    def wrap(self, wrap_this=None):
        if wrap_this is None:
            return self if USE_COLOR else self.__class__('')
        else:
            if USE_COLOR:
                return self + wrap_this - self
            else:
                return wrap_this

    def __call__(self, wrap_this=None):
        """This sets the color (no arguments) or wraps a str (1 arg)"""
        if wrap_this is None:
            self.now()
        else:
            return self.wrap(wrap_this)

    def __neg__(self):
        """This negates the effect of the current color"""
        return self.negate()

    def __rsub__(self, other):
        """Implemented to make using negatives easier"""
        return other + (-self)

    def _remove(self):
        """Don't use directly. Will find best match for negative of current color."""
        if self == '':
            return ''
        try:
            if self[:2] == '\033[' and self[-1] == 'm':
                v = self[2:-1].split(';')
                n = list(map(int, v))
                if len(n) == 1 or (len(n) == 3 and n[1] == 5 and n[0] in (38, 48)):
                    if 30 <= n[0] <= 39:
                        return '\033[39m'
                    elif 40 <= n[0] <= 49:
                        return '\033[49m'
                    elif n[0] in (1, 2, 4, 5, 7, 8):
                        return '\033['+str(n[0]+20)+'m'
                    elif n[0] in (21, 22, 24, 25, 27, 28):
                        return '\033['+str(n[0]-20)+'m'
        except ValueError:
            pass
        return '\033[0m'

    def __enter__(self):
        if USE_COLOR:
            STDOUT.write(self)
        return self

    def __exit__(self, type, value, traceback):
        if USE_COLOR:
            STDOUT.write(-self)
        return False


def ansi_color(n):
    """Return an ANSI escape sequence given a number."""
    return Style('\033[' + str(n) + 'm') if USE_COLOR else Style('')


def extended_ansi_color(n, begin=38):
    """Return an ANSI extended color given number."""
    return Style('\033[' + str(begin) + ';5;' + str(n) + 'm') if USE_COLOR else Style('')


class _COLOR_NAMES(object):

    """This creates color names given a modifier value (FG, BG)"""

    def __init__(self, val):
        self.val = val
        self.BLACK = ansi_color(0+self.val)
        self.RED = ansi_color(1+self.val)
        self.GREEN = ansi_color(2+self.val)
        self.YELLOW = ansi_color(3+self.val)
        self.BLUE = ansi_color(4+self.val)
        self.MAGENTA = ansi_color(5+self.val)
        self.CYAN = ansi_color(6+self.val)
        self.WHITE = ansi_color(7+self.val)
        self.RESET = ansi_color(9+self.val)

    def regular(self, val):
        """Access colors by value."""
        return ansi_color(val + self.val)

    def extended(self, val):
        """Return the extended color scheme color for a value."""
        return extended_ansi_color(val, self.val + 8)

    def __call__(self, val):
        """Shortcut to provide way to access colors by number"""
        return self.regular(val)

    def __getitem__(self, val):
        """Shortcut to provide way to access extended colors by number"""
        return self.extended(val)

    def __iter__(self):
        """Iterates through all colors in extended colorset."""
        return (self.extended(i) for i in range(256))

    def __neg__(self):
        """Allows clearing a color"""
        return self.RESET

    def __rsub__(self, other):
        return other + (-self)


class COLOR(object):

    def __init__(self):
        self.BOLD = ansi_color(1)
        self.DIM = ansi_color(2)
        self.UNDERLINE = ansi_color(4)
        self.BLINK = ansi_color(5)
        self.REVERSE = ansi_color(7)
        self.HIDDEN = ansi_color(8)

        self.FG = _COLOR_NAMES(30)
        self.BG = _COLOR_NAMES(40)

        self.BLACK = self.FG.BLACK
        self.RED = self.FG.RED
        self.GREEN = self.FG.GREEN
        self.YELLOW = self.FG.YELLOW
        self.BLUE = self.FG.BLUE
        self.MAGENTA = self.FG.MAGENTA
        self.CYAN = self.FG.CYAN
        self.WHITE = self.FG.WHITE

        self.RESET = ansi_color(0)
        self.DO_NOTHING = Style('')

    def __call__(self, color):
        return Style(color)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        STDOUT.write(ansi_color(0))
        return False


COLOR = COLOR()


@contextmanager
def with_color(color='', out=None):
    """Sets the color to a given color or style,
    resets when done,
    even if an exception is thrown. Optional ``out`` to give a
    different output channel (defaults to STDOUT, which is set
    to sys.stdout)."""

    if out is None:
        out = STDOUT
    out.write(str(color))
    try:
        yield
    finally:
        out.write(ansi_color(0))

__all__ = ['COLOR', 'with_color', 'ansi_color', 'extended_ansi_color', 'Style', 'USE_COLOR', 'STDOUT']
