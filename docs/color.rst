.. _guide-color:

Color tools
===========

.. versionadded:: 1.6.0


The purpose of the `plumbum.color` library is to make adding
color to Python easy and safe. Color is often a great
addition to shell scripts, but not a necessity, and implementing it properly 
is tricky. It is easy to end up with an unreadable color stuck on your terminal or
with random unreadable symbols around your text. With the color module, you get quick,
safe access to ANSI colors and attributes for your scripts. The module also provides an
API for creating other colorschemes for other systems using escapes.

.. note:: Enabling color

    The ANSI Style assumes that only a terminal on a posix-identity
    system can display color. You can force the use of color globally by setting
    ``Style.use_color=True``.


Color Factory
=============

Colors are accessed through the ``COLOR`` object, which is an instance of a StyleFactory.
The ``COLOR`` object has the following properties:

    ``FG`` and ``BG``
      The forground and background colors, reset to default with ``COLOR.FG.RESET``
      or ``-COLOR.FG`` and likewise for ``BG``. (Named forground colors are available
      directly as well). The primary colors, ``BLACK``, ``RED``, ``GREEN``, ``YELLOW``,
      ``BLUE``, ``MAGENTA``, ``CYAN``, ``WHITE``, as well as ``RESET``, are available.
      You can also access colors numerically with ``COLOR.FG(n)``, for the standard colors,
      and ``COLOR.FG[n]`` for the extended 256 color codes, and likewise for ``BG``.
    ``BOLD``, ``DIM``, ``UNDERLINE``, ``BLINK``, ``REVERSE``, and ``HIDDEN``
      All the `ANSI` modifiers are available, as well as their negations, sush as ``-COLOR.BOLD`` or ``COLOR.BOLD.RESET``, etc.
    ``RESET``
      The global reset will restore all properties at once.
    ``DO_NOTHING``
      Does nothing at all, but otherwise acts like any ``Style`` object. It is its own inverse. Useful for ``cli`` properties.

A color can be used directly as if it was a string, for adding to strings or printing.
Calling a color without an argument will send the color to stdout. Calling a
color with an argument will wrap the string in the color and the matching negation.
(to avoid accedintally sending a color to stdout, you can also use `[]` syntax).
Any color can be used as the target of a with statement, and normal color
will be restored on exiting the with statement, even when an Exception occurs.
 
An example of the usage of ``COLOR``::

    from plumbum import COLOR
    with COLOR.FG.RED:
        print('This is in red')
        COLOR.FG.GREEN()
        print('This is green')
    print('This is completly restored, even if an exception is thrown!')

We could have used the shortcut ``COLOR.GREEN()`` instead.  If we had a non-foreground color
style active, such as ``COLOR.UNDERLINE`` or ``COLOR.BG.YELLOW``, then the context manager
will not reset those properties; it only resets properties it sets.
You can also use ``COLOR`` directly as a context manager if you only want to 
restore all color after a block. If you call
``COLOR.from_ansi(...)``, you can manually pass in any `ANSI` escape sequence.

Further examples of manipulations possible with the library::

    print(COLOR.FG.YELLOW('This is yellow') + ' And this is normal again')
    with COLOR:
        print('It is always a good idea to be in a context manager, to avoid being',
              'left with a colored terminal if there is an exception!')
        COLOR.FG.RED()
        print(COLOR.BOLD("This is red, bold, and exciting!"), "And this is red only.")
        print(COLOR.BG.CYAN + "This is red on a cyan background." + COLOR.RESET)
        print(COLOR.FG[42] + "If your terminal supports 256 colors, this is colorful!" + COLOR.RESET)
        COLOR.YELLOW()
        print('Colors made', COLOR.UNDERLINE + 'very' - COLOR.UNDERLINE, 'easy!')



256 color support
-----------------

The library support 256 colors through numbers, names or HEX html codes. You can access them
as ``COLOR.FG[12]``, ``COLOR.FG['Light_Blue']``, ``COLOR.FG['LightBlue']``, or ``COLOR.FG['#0000FF']``. The supported colors are:

.. raw:: html
    :file: _color_list.html

The Classes
-----------

The library consists of three primary classes, the ``Color`` class, the ``Style`` class, and the ``StyleFactory`` class. The following
portion of this document is primarily dealing with the working of the system, and is meant to facilitate extensions or work on the system.

The ``Color`` class provides meaning to the concept of color, and can provide a variety of representations for any color. It
can be initialised from r,g,b values, or hex codes, 256 colornames, or the simple color names via classmethods. If initialized
without arguments, it is the reset color. It also takes an fg True/False argument to indicate which color it is. You probably will
not be interacting with the Color class directly, and you probably will not need to subclass it, though new extensions to the
representations it can produce are welcome.

The ``Style`` class hold two colors and a dictionary of attributes. It is the workhorse of the system and is what is produced
by the ``COLOR`` factory. It holds ``Color`` as ``.color_class``, which can be overridden by subclasses (again, this usually is not needed).
To create a color representation, you need to subclass ``Style`` and give it a working ``__str__`` definition. ``ANSIStyle`` is derived
from ``Style`` in this way.

The factories, ``ColorFactory`` and ``StyleFactory``, are factory classes that are meant to provide simple access to 1 style Style classes. To use,
you need to initialize an object of ``StyleFactory`` with your intended Style. For example, ``COLOR`` is created by::

    COLOR = StyleFactory(ANSIStyle)

HTML Subclass Example
---------------------

For example, if you wanted to create an HTMLStyle and HTMLCOLOR, you could do::

    class HTMLStyle(Style):

        attribute_names = set(('bold','em'))

        def __str__(self):
            if self.reset:
                raise ResetNotSupported("HTML does not support global resets!") 
            result = ''
    
            if self.fg and not self.fg.reset:
                result += '<font color="{0}">'.format(self.fg.html_hex_code)
            if self.bg and not self.bg.reset:
                result += '<span style="background-color: {0}">'.format(self.fg.html_hex_code)
            if 'bold' in self.attributes and self.attributes['bold']:
                result += '<b>'
            if 'em' in self.attributes and self.attributes['em']:
                result += '<em>'
    
            if self.fg and self.fg.reset:
                result += '</font>'
            if self.bg and self.bg.reset:
                result += '</span>'
            if 'bold' in self.attributes and not self.attributes['bold']:
                result += '</b>'
            if 'em' in self.attributes and not self.attributes['em']:
                result += '</em>'
    
            return result


    HTMLCOLOR = StyleFactory(HTMLStyle)
    
This doesn't support global RESETs, but otherwise is a working implementation. This is an example of how easy it is to add support for other output formats.

An example of usage::

    >>> (HTMLCOLOR.BOLD + HTMLCOLOR.RED)("This is colored text")
    '<font color="#800000"><b>This is colored text</font></b>'


The above colortable can be generated with::

    with open('_color_list.html', 'wt') as f:
        print('<ol start=0>', file=f)
        for color in HTMLCOLOR:
            print("  <li>{0} <code>{1}</code> {2} </li>"
                  .format(color("&#x25a0"),
                          color.fg.html_hex_code,
                          color.fg.name_camelcase), file=f)
        print('</ol>', file=f)


.. note::
    
    ``HTMLStyle`` is implemented in the library, as well, with the
    ``HTMLCOLOR`` object available in ``plumbum.color``.

See Also
--------
* `colored <https://pypi.python.org/pypi/colored>`_ Another library with 256 color support
* `colorama <https://pypi.python.org/pypi/colorama>`_ A library that supports colored text on Windows,
    can be combined with plumbum (if you force ``use_color``)
