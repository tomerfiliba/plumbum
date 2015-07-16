"""
Color-related utilities. Feel free to use any color library on
the ``with_color`` statement.

The ``COLOR`` object provides ``BG`` and ``FG`` to access colors,
and attributes like bold and
underlined text. It also provides ``RESET`` to recover the normal font.

With the ``Style`` string subclass being used, any color can be
directly called or given to a with statement.
"""

from __future__ import print_function
import sys
import os
from contextlib import contextmanager
from plumbum.color.names import color_names_full as names, color_html_full as html
from plumbum.color.names import color_names_simple as simple_colors, attributes_simple as simple_attributes
from functools import partial

camel_names = [n.replace('_',' ').title().replace(' ','') for n in names]

class Style(str):
    """This class allows the color change strings to be called directly
    to write them to stdout, and can be called in a with statement.
    The use_color property causes this to return '' for colors, but only on
    new instances of the object."""

    use_color = sys.stdout.isatty() and os.name == "posix"
    stdout = sys.stdout

    def negate(self):
        """This negates the effect of the current color"""
        return self.__class__(self._remove() if self.__class__.use_color else '')

    def now(self, wrap_this=None):
        self.stdout.write(self.wrap(wrap_this))

    def wrap(self, wrap_this=None):
        if wrap_this is None:
            return self if self.__class__.use_color else self.__class__('')
        else:
            if self.__class__.use_color:
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

    def __sub__(self, other):
       """Implemented to make muliple Style objects work"""
       return self + (-other)

    def __rsub__(self, other):
        """Implemented to make using negatives easier"""
        return other + (-self)

    def __add__(self, other):
       return self.__class__(super(Style, self).__add__(other))

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
                else:
                    return ''
        except ValueError:
            pass
        return '\033[0m'

    def __enter__(self):
        if self.__class__.use_color:
            self.stdout.write(self)
        return self

    def __exit__(self, type, value, traceback):
        if self.__class__.use_color:
            self.stdout.write(-self)
        return False


    @classmethod
    def ansi_color(cls, n):
        """Return an ANSI escape sequence given a number."""
        return cls('\033[' + str(n) + 'm') if cls.use_color else cls('')

    @classmethod
    def extended_ansi_color(cls, n, begin=38):
        """Return an ANSI extended color given number."""
        return cls('\033[' + str(begin) + ';5;' + str(n) + 'm') if cls.use_color else cls('')


def _get_style_color(color, ob):
    'Gets a color, intended to be used in discriptor protocol'
    return Style.ansi_color((simple_colors.index(color) if color != 'reset' else 9) +ob.val)


def _get_style_attribute(attribute, ob):
    'Gets an attribute, intended to be used in discriptor protocol'
    return Style.ansi_color(simple_attributes[attribute] if attribute != 'reset' else 0)


class ColorCollection(object):

    """This creates color names given a modifier value (FG, BG)"""


    def __init__(self, val):
        self.val = val

    @property
    def RESET(self):
        return _get_style_color('reset',self)

    def from_name(self, name):
        'Gets the index of a name, raises key error if not found'
        if name in names:
            return Style.extended_ansi_color(names.index(name), self.val + 8)
        if name in camel_names:
            return Style.extended_ansi_color(camel_names.index(name), self.val + 8)
        if name in html:
            return Style.extended_ansi_color(html.index(name, 1), self.val + 8) # Assuming second #000000 is better
        raise KeyError(name)

    def regular(self, val):
        """Access colors by value."""
        return Style.ansi_color(val + self.val)

    def extended(self, val):
        """Return the extended color scheme color for a value."""
        return Style.extended_ansi_color(val, self.val + 8)

    def __call__(self, val):
        """Shortcut to provide way to access colors by number"""
        return self.regular(val)

    def __getitem__(self, val):
        """Shortcut to provide way to access extended colors by number, name, or html hex code"""
        try:
            return self.from_name(val)
        except KeyError:
            return self.extended(val)

    def __iter__(self):
        """Iterates through all colors in extended colorset."""
        return (self.extended(i) for i in range(256))

    def __neg__(self):
        """Allows clearing a color"""
        return self.RESET

    def __rsub__(self, other):
        return other + (-self)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        """This resets a FG/BG color or all colors,
        due to different definition of RESET."""

        Style.stdout.write(self.RESET)
        return False

# Adding the color name shortcuts
for item in simple_colors:
    setattr(ColorCollection, item.upper(), property(partial(_get_style_color, item), doc='Shortcut for '+item))

class ColorFactory(ColorCollection):

    """Singleton. Holds font styles, FG and BG objects representing colors, and
    imitates the FG object to some degree."""

    def __init__(self):
        self.val = 30 # This acts like FG color

        self.FG = ColorCollection(30)
        self.BG = ColorCollection(40)

        self.DO_NOTHING = Style('')

    def __call__(self, color):
        """Calling COLOR is a shortcut for Style(color)"""
        return Style(color)


for item in simple_attributes:
    setattr(ColorFactory, item.upper(), property(partial(_get_style_attribute, item), doc='Shortcut for '+item))
setattr(ColorFactory, 'reset'.upper(), property(partial(_get_style_attribute, 'reset'), doc='Shortcut for reset'))


COLOR = ColorFactory()


@contextmanager
def with_color(color='', out=None):
    """Sets the color to a given color or style,
    resets when done,
    even if an exception is thrown. Optional ``out`` to give a
    different output channel (defaults to sys.stdout)."""

    if out is None:
        out = sys.stdout
    out.write(str(color))
    try:
        yield
    finally:
        out.write(Style.ansi_color(0))

__all__ = ['COLOR', 'ColorCollection', 'with_color', 'Style']
