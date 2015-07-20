.. _guide-color:

Color tools
-----------

.. versionadded:: 1.6.0


The purpose of the `plumbum.color` library is to make adding
text styles (such as color) to Python easy and safe. Color is often a great
addition to shell scripts, but not a necessity, and implementing it properly 
is tricky. It is easy to end up with an unreadable color stuck on your terminal or
with random unreadable symbols around your text. With the color module, you get quick,
safe access to ANSI colors and attributes for your scripts. The module also provides an
API for creating other color schemes for other systems using escapes.

.. note:: Enabling color

    ``ANSIStyle`` assumes that only a terminal on a posix-identity
    system can display color. You can force the use of color globally by setting
    ``COLOR.use_color=True``.

The Color Factory
=================

Styles are accessed through the ``COLOR`` object, which is an instance of a StyleFactory.
The ``COLOR`` object has the following properties:

    ``FG`` and ``BG``
      The foreground and background colors, reset to default with ``COLOR.FG.RESET``
      or ``~COLOR.FG`` and likewise for ``BG``. (Named foreground colors are available
      directly as well). The first 16 primary colors, ``BLACK``, ``RED``, ``GREEN``, ``YELLOW``,
      ``BLUE``, ``MAGENTA``, ``CYAN``, etc, as well as ``RESET``, are available.
      You can also access colors numerically with ``COLOR.FG(n)`` or  ``COLOR.FG(n)``
      with the extended 256 color codes. These
      are ``ColorFactory`` instances.
    ``BOLD``, ``DIM``, ``UNDERLINE``, ``ITALICS``, ``REVERSE``, ``STRIKEOUT``, and ``HIDDEN``
      All the `ANSI` modifiers are available, as well as their negations, such as ``~COLOR.BOLD`` or ``COLOR.BOLD.RESET``, etc.
    ``RESET``
      The global reset will restore all properties at once.
    ``DO_NOTHING``
      Does nothing at all, but otherwise acts like any ``Style`` object. It is its own inverse. Useful for ``cli`` properties.

The ``COLOR`` object can be used in a with statement, which resets the color on leaving 
the statement body. (The ``FG`` and ``BG`` also can be put in with statements, and they
will restore the foreground and background color, respectively). Although it does support
some of the same things as a Style, its primary purpose is to generate Styles.  

If you call ``COLOR.from_ansi(seq)``, you can manually pass in any `ANSI` escape sequence,
even complex or combined ones. ``COLOR.rgb(r,g,b)`` will create a color from an
input red, green, and blue values (integers from 0-255). ``COLOR.hex(code)`` will allow
you to input an html style hex sequence. These work on ``FG`` and ``BG`` too. The ``repr`` of
styles is smart and will show you the closest color to the one you selected if you didn't exactly
select a color through RGB. 

Style manipulations
===================

Safe color manipulations refer to changes that reset themselves at some point. Unsafe manipulations
must be manually reset, and can leave your terminal color in an unreadable state if you forget
to reset the color or encounter an exception. If you do get the color unset on a terminal, the
following, typed into the command line, will restore it:

.. code:: bash

    $ python -m plumbum.color

Unsafe Manipulation
^^^^^^^^^^^^^^^^^^^

Styles have two unsafe operations: Concatenation (with ``+`` and a string) and calling ``.now()`` without
arguments (directly calling a style without arguments is also a shortcut for ``.now()``). These two
operations do not restore normal color to the terminal by themselves. To protect their use,
you should always use a context manager around any unsafe operation.

An example of the usage of unsafe ``COLOR`` manipulations inside a context manager::

    from plumbum import COLOR

    with COLOR:
        COLOR.FG.RED()
        print('This is in red')
        COLOR.GREEN()
        print('This is green ' + COLOR.UNDERLINE + 'and now also underlined!')
        print('Underlined' - COLOR.UNDERLINE + ' and not underlined but still red') 
    print('This is completly restored, even if an exception is thrown!')

Output:

  .. raw:: html
    
    <p><font color="#800000">This is in red</font><br/>
    <font color="#008000">This is in green <span style="text-decoration: underline;">and now also underlined!</span></font><br/>
    <font color="#008000"><span style="text-decoration: underline;">Underlined</span> and not underlined but still green.</font><br/>
    This is completly restored, even if an exception is thrown! </p>

We can use ``COLOR`` instead of ``COLOR.FG`` for foreground colors.  If we had used ``COLOR.FG``
as the context manager, then non-foreground properties, such as ``COLOR.UNDERLINE`` or
``COLOR.BG.YELLOW``, would not have reset those properties. Each attribute,
as well as ``FG``, ``BG``, and ``COLOR`` all have inverses in the ANSI standard. They are
accessed with ``~``, ``-``, or ``.RESET``, and can be used to manually make these operations
safer, but there is a better way.

Safe Manipulation
^^^^^^^^^^^^^^^^^

All other operations are safe; they restore the color automatically. The first, and hopefully
already obvious one, is using a Style rather than a ``COLOR`` or ``COLOR.FG`` object in a ``with`` statement.
This will set the color (using sys.stdout by default) to that color, and restore color on leaving.

The second method is to manually wrap a string. This can be done with ``color.wrap("string")``,
``"string" << color``, ``color >> "string"``, or ``color["string"]``.
These produce strings that can be further manipulated or printed.

.. note::

  ``color * "string"`` is also a valid way to wrap strings and has a well understood order of
  operations by most people writing or reading code. Under some conditions, having an operator
  that takes preference over concatination is prefered. However, a bug in Python 2.6 causes right
  multiplication with a string, such as ``"string" * color``, to be impossible to implement.
  This was fixed in all newer Pythons. If you are not planning on `supporting Python
  2.6 <http://www.curiousefficiency.org/posts/2015/04/stop-supporting-python26.html>`_, feel
  free to use this method.

Finally, you can also print a color to stdout directly using ``color("string")`` or
``color.print("string")``. Since the first can be an unsafe operation if you forget an arguement,
you may prefer the latter. This
has the same syntax as the Python 3 print function. In Python 2, if you do not have
``from __future__ import print_function`` enabled, ``color.print_("string")`` is provided as
an alternative, following the PyQT convention for method names that match reserved Python syntax.

An example of safe manipulations::

    COLOR.FG.YELLOW('This is yellow', end='')
    print(' And this is normal again.')
    with COLOR.RED:
        print('Red color!')
        with COLOR.BOLD:
            print("This is red and bold.")
        print("Not bold, but still red.")
    print("Not red color or bold.")
    print("This is bold and colorful!" << (COLOR.MAGENTA + COLOR.BOLD), "And this is not.")

Output:

  .. raw:: html

    <p><font color="#808000">This is yellow</font> And this is normal again.<br/>
    <font color="#800000">Red color!<br/>
    <b>This is red and bold.<br/>
    </b>Not bold, but still red.<br/>
    </font>Not red color or bold.<br/>
    <font color="#800080"><b>This is bold and colorful!</b></font> And this is not.</p>

Style Combinations
^^^^^^^^^^^^^^^^^^

You can combine styles with ``+``, ``*``, ``<<``, or ``>>``, and they will create a new combined Style object. Colors will not be "summed" or otherwise combined; the rightmost color will be used (this matches the expected effect of
applying the Styles individually to the strings). However, combined Styles are intelligent and know how to reset just the properties that they contain. As you have seen in the example above, the combined style ``(COLOR.MAGENTA + COLOR.BOLD)`` can be used in any way a normal Style can.

256 Color Support
=================

While this library supports full 24 bit colors through escape sequences,
the library has speciall support for the "full" 256 colorset through numbers,
names or HEX html codes. Even if you use 24 bit color, the closest name is displayed
in the ``repr``. You can access the colors as
as ``COLOR.FG(12)``, ``COLOR.FG('Light_Blue')``, ``COLOR.FG('LightBlue')``, or ``COLOR.FG('#0000FF')``.
You can also iterate or slice the ``COLOR``, ``COLOR.FG``, or ``COLOR.BG`` objects. Slicing even
intelegently downgrades to the simple version of the codes if it is within the first 16 elements.
The supported colors are:

.. raw:: html
    :file: _color_list.html


The Classes
===========

The library consists of three primary classes, the ``Color`` class, the ``Style`` class, and the ``StyleFactory`` class. The following
portion of this document is primarily dealing with the working of the system, and is meant to facilitate extensions or work on the system.

The ``Color`` class provides meaning to the concept of color, and can provide a variety of representations for any color. It
can be initialised from r,g,b values, or hex codes, 256 color names, or the simple color names via classmethods. If initialized
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

Subclassing Style
^^^^^^^^^^^^^^^^^

For example, if you wanted to create an HTMLStyle and HTMLCOLOR, you could do::

    class HTMLStyle(Style):
        attribute_names = dict(bold='b', em='em', li='li', code='code')
        end = '<br/>\n'

        def __str__(self):
            result = ''

            if self.bg and not self.bg.reset:
                result += '<span style="background-color: {0}">'.format(self.bg.html_hex_code)
            if self.fg and not self.fg.reset:
                result += '<font color="{0}">'.format(self.fg.html_hex_code)
            for attr in sorted(self.attributes):
                if self.attributes[attr]:
                    result += '<' + self.attribute_names[attr] + '>'
     
            for attr in reversed(sorted(self.attributes)):
                if not self.attributes[attr]:
                    result += '</' + self.attribute_names[attr].split()[0] + '>'
            if self.fg and self.fg.reset:
                result += '</font>'
            if self.bg and self.bg.reset:
                result += '</span>'

            return result

    HTMLCOLOR = StyleFactory(HTMLStyle)
    
This doesn't support global RESETs, since that's not how HTML works, but otherwise is a working implementation. This is an example of how easy it is to add support for other output formats.

An example of usage::

    >>> "This is colored text" << HTMLCOLOR.BOLD + HTMLCOLOR.RED
    '<font color="#800000"><b>This is colored text</b></font>'


The above color table can be generated with::

    with open('_color_list.html', 'wt') as f:
        with HTMLCOLOR.OL:
            for color in HTMLCOLOR:
                HTMLCOLOR.LI(
                    "&#x25a0;" << color,
                    color.fg.html_hex_code << HTMLCOLOR.CODE,
                    color.fg.name_camelcase)


.. note::
    
    ``HTMLStyle`` is implemented in the library, as well, with the
    ``HTMLCOLOR`` object available in ``plumbum.color``. It was used
    to create the colored output in this document, with small changes
    because ``COLOR.RESET`` cannot be supported with HTML.

See Also
========

* `colored <https://pypi.python.org/pypi/colored>`_ Another library with 256 color support
* `colorama <https://pypi.python.org/pypi/colorama>`_ A library that supports colored text on Windows,
    can be combined with Plumbum.color (if you force ``use_color``, doesn't support all extended colors)
