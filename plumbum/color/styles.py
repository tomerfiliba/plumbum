"""
With the ``Style`` class, any color can be directly called or given to a with statement.
"""

from __future__ import print_function
import sys
import os
import re
from copy import copy
from plumbum.color.names import color_names_full, color_html_full
from plumbum.color.names import color_names_simple, color_html_simple, valid_attributes, from_html
from plumbum.color.names import find_nearest_color, find_nearest_simple_color, attributes_ansi

__all__ = ['Color', 'Style', 'ANSIStyle', 'ColorNotFound', 'AttributeNotFound']


_lower_camel_names = [n.replace('_', '') for n in color_names_full]


class ColorNotFound(Exception):
    pass


class AttributeNotFound(Exception):
    pass


class Color(object):
    """This class stores the idea of a color, rather than a specific implementation.
    It provides as many different tools for representations as possible, and can be subclassed
    to add more represenations. ``.from_any`` provides a quick-init shortcut.

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


    def __init__(self, r_or_color=None, g=None, b=None, fg=True):
        """This works from color values, or tries to load non-simple ones."""

        self.fg = fg
        self.reset = True # Starts as reset color
        self.rgb = (0,0,0)
        self.simple = False
        self.exact = True # Sets to false if interpolation done

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
        if self.simple:
            self.number = find_nearest_simple_color(*self.rgb)
            self.exact = self.rgb == from_html(color_html_simple[self.number])
        else:
            self.number = find_nearest_color(*self.rgb)
            self.exact = self.rgb == from_html(color_html_full[self.number])

        self.reset = False

    @classmethod
    def from_simple(cls, color, fg=True):
        """Creates a color from simple name or color number"""
        self = cls(fg=fg)
        self._from_simple(color)
        return self

    def _from_simple(self, color):
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
        """The (closest) name of the current color"""
        if self.reset:
            return 'reset'
        elif self.simple:
            return color_names_simple[self.number]
        else:
            return color_names_full[self.number]

    def __repr__(self):
        name = ' Simple' if self.simple else ''
        name += '' if self.fg else ' Background'
        name += ' ' + self.name.replace('_',' ').title()
        name += '' if self.exact else (" "+str(self.rgb))
        return name[1:]

    def __eq__(self, other):
        if self.reset:
            return other.reset
        else:
            return (self.number == other.number
                    and self.rgb == other.rgb
                    and self.simple == other.simple)

    @property
    def ansi_sequence(self):
        if not self.__class__.use_color:
            return ''
        else:
            return '\033[' + ';'.join(map(str, self.ansi_codes)) + 'm'

    @property
    def ansi_codes(self):
        ansi_addition = 30 if self.fg else 40

        if self.reset:
            return (ansi_addition+9,)
        elif self.simple:
            return (self.number+ansi_addition,)
        else:
            return (ansi_addition+8, 5, self.number)

    @property
    def html_hex_code(self):
        if reset:
            return '#000000'
        return color_html_simple[self.number] if self.simple else color_html_full[self.number]

    def __str__(self):
        return self.name



class Style(object):
    """This class allows the color changes to be called directly
    to write them to stdout, ``[]`` calls to wrap colors (or the ``.wrap`` method)
    and can be called in a with statement.
    The ``use_color`` property causes this to return '' for colors"""

    use_color = sys.stdout.isatty() and os.name == "posix"
    stdout = sys.stdout
    color_class = Color
    attribute_names = valid_attributes # a set of valid names

    def __init__(self, attributes=None, fgcolor=None, bgcolor=None, reset=False):
        self.attributes = attributes if attributes is not None else dict()
        self.fg = fgcolor
        self.bg = bgcolor
        self.reset = reset
        invalid_attributes = set(self.attributes) - self.attribute_names
        if len(invalid_attributes) > 0:
            raise AttributeNotFound("Attribute(s) not valid: " + ", ".join(invalid_attributes))

    @classmethod
    def from_color(cls, color):
        if color.fg:
            self = cls(fgcolor=color)
        else:
            self = cls(bgcolor=color)
        return self


    def invert(self):
        """This resets current color(s) and flips the value of all
        attributes present"""

        other = self.__class__()

        # Opposite of reset is reset
        if self.reset:
            other.reset = True
            return other

        # Flip all attributes
        for attribute in self.attributes:
            other.attributes[attribute] = not self.attributes[attribute]

        # Reset only if color present
        if self.fg:
            other.fg = self.fg.__class__()

        if self.bg:
            other.bg = self.bg.__class__()

        return other

    def __copy__(self):
        """Copy is supported, will make dictionary and colors unique."""
        result = self.__class__()
        result.reset = self.reset
        result.fg = copy(self.fg)
        result.bg = copy(self.bg)
        result.attributes = copy(self.attributes)
        return result

    def __neg__(self):
        """This negates the effect of the current color"""
        return self.invert()

    def __sub__(self, other):
       """Implemented to make muliple Style objects work"""
       return self + (-other)

    def __rsub__(self, other):
        """Implemented to make using negatives easier"""
        return other + (-self)

    def __add__(self, other):
        """Adding two matching Styles results in a new style with
        the combination of both. Adding with a string results in
        the string concatiation of a style.

        Addition is non-communitive, with the rightmost Style property
        being taken if both have the same property."""
        if type(self) == type(other):
            result = copy(other)

            result.reset = self.reset or other.reset
            for attribute in self.attributes:
                if attribute not in result.attributes:
                    result.attributes[attribute] = self.attributes[attribute]
            if not result.fg:
                result.fg = self.fg
            if not result.bg:
                result.bg = self.bg
            return result
        else:
            return other.__class__(self) + other

    def __radd__(self, other):
        """This only gets called if the string is on the left side."""
        return other + other.__class__(self)

    def wrap(self, wrap_this):
        return self + wrap_this - self

    def __call__(self, printable=None):
        if printable:
            self.stdout.write(self.wrap(printable))
        else:
            self.stdout.write(str(self))

    def __getitem__(self, wrap_this):
        """The [] syntax is supported for wrapping"""
        return self.wrap(wrap_this)

    def __enter__(self):
        """Context manager support"""
        self.stdout.write(str(self))

    def __exit__(self, type, value, traceback):
        """Runs even if exception occured, does not catch it."""
        self.stdout.write(str(-self))
        return False

    @property
    def ansi_codes(self):
        if self.reset:
            return [0]

        codes = []
        for attribute in self.attributes:
            if self.attributes[attribute]:
                codes.append(attributes_ansi[attribute])
            else:
                codes.append(20+attributes_ansi[attribute])

        if self.fg:
            codes.extend(self.fg.ansi_codes)

        if self.bg:
            self.bg.fg = False
            codes.extend(self.bg.ansi_codes)

        return codes

    @property
    def ansi_sequence(self):
        return '\033[' + ';'.join(map(str, self.ansi_codes)) + 'm'

    def __repr__(self):
        name = self.__class__.__name__
        attributes = ', '.join(a for a in self.attributes if self.attributes[a])
        neg_attributes = ', '.join('-'+a for a in self.attributes if not self.attributes[a])
        colors = ', '.join(repr(c) for c in [self.fg, self.bg] if c)
        string = '; '.join(s for s in [attributes, neg_attributes, colors] if s)
        if self.reset:
            string = 'reset'
        return "<{0}: {1}>".format(name, string if string else 'empty')

    def __eq__(self, other):
        if type(self) == type(other):
            if self.reset:
                return other.reset
            else:
                return (self.attributes == other.attributes
                        and self.fg == other.fg
                        and self.bg == other.bg)
        else:
            return str(self) == other

    def __str__(self):
        raise NotImplemented("This is a base style, does not have an representation")

    # TODO: Support buffer interface?


    @classmethod
    def from_ansi(cls, ansi_string):
        """This generated a style from an ansi string."""
        result = self.__class__()
        reg = re.compile('\033' + r'\[([\d;]+)m')
        res = reg.search(ansi_string)
        for group in res.groups:
            sequence = map(int,group.split(';'))
            result.add_ansi(sequence)

    def add_ansi(self, sequence):
        """Adds a sequence of ansi numbers to the class"""

        values = iter(sequence)
        try:
            while True:
                value = next(value)
                if value == 38 or value == 48:
                    fg = value == 38
                    if next(values) != 5:
                        raise ColorNotFound("the value 5 should follow a 38 or 48")
                    value = next(values)
                    if fg:
                        self.fg = self.color_class.from_full(value)
                    else:
                        self.bg = self.color_class.from_full(value, fg=False)
                elif value==0:
                    self.reset = True
                elif value in ansi_attributes.values():
                    for name in ansi_attributes:
                        if value == ansi_attributes[name]:
                            self.attributes[name] = True
                elif value in (20+n for n in ansi_attributes.values()):
                    for name in ansi_attributes:
                        if value == ansi_attributes[name] + 20:
                            self.attributes[name] = False
                elif 30 <= value <= 37:
                    self.fg = self.color_class.from_simple(value-30)
                elif 40 <= value <= 47:
                    self.bg = self.color_class.from_simple(value-40, fg=False)
                elif value == 39:
                    self.fg = self.color_class()
                elif value == 49:
                    self.bg = self.color_class(fg=False)
                else:
                    raise ColorNotFound("The code {0} is not recognised".format(value))
        except StopIteration:
            return


class ANSIStyle(Style):
    attribute_names = set(attributes_ansi)

    def __str__(self):
        if self.use_color:
            return self.ansi_sequence
        else:
            return ''

