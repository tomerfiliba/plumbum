.. _guide-colors:

Colors
------

.. versionadded:: 1.6


The purpose of the `plumbum.colors` library is to make adding
text styles (such as color) to Python easy and safe. Color is often a great
addition to shell scripts, but not a necessity, and implementing it properly 
is tricky. It is easy to end up with an unreadable color stuck on your terminal or
with random unreadable symbols around your text. With the color module, you get quick,
safe access to ANSI colors and attributes for your scripts. The module also provides an
API for creating other color schemes for other systems using escapes.

.. note:: Enabling color

    ``ANSIStyle`` assumes that only a terminal can display color, and looks at
    the value of the environment variable ``TERM``. You can force the use of color globally by setting
    ``colors.use_color=4`` (The levels 0-4 are available, with 0 being off). See this :ref:`note <guide-usecolors>`
    for more options.

Quick start
===========

Colors (``red``, ``green``, etc.), attributes (``bold``, ``underline``, etc.)
and general styles (``warn``, ``info``, etc.)
are in ``plumbum.colors``. Combine styles with ``&``, apply to a string with ``|``. So, to output a
warning you would do

.. code-block:: python

    from plumbum.colors import warn
    print(warn | "This is a warning.")

.. raw:: html

    <p><font color="#800000">This is a warning.</font>

To create a custom style you would do

.. code-block:: python

    from plumbum import colors
    print(colors.green & colors.bold | "This is green and bold.")

.. raw:: html
    
    <font color="#008000"><b>This is green and bold.</b></font>

You can use rgb colors, too:

.. code-block:: python

    print(colors.rgb(0,255,0) | "This is also green.")

.. raw:: html

    <font color="#00ff00">This is also green</font>


Generating Styles
=================

Styles are accessed through the ``plumbum.colors`` object. This has the following available objects:

    ``fg`` and ``bg``
      The foreground and background colors, reset to default with ``colors.fg.reset``
      or ``~colors.fg`` and likewise for ``bg``.
    ``bold``, ``dim``, ``underline``, ``italics``, ``reverse``, ``strikeout``, and ``hidden``
      All the `ANSI` modifiers are available, as well as their negations, such
      as ``~colors.bold`` or ``colors.bold.reset``, etc.
    ``reset``
      The global reset will restore all properties at once.
    ``do_nothing``
      Does nothing at all, but otherwise acts like any ``Style`` object. It is its own inverse. Useful for ``cli`` properties.
      
    Styles loaded from a stylesheet dictionary, such as ``warn`` and ``info``.
      These allow you to set standard styles based on behavior rather than colors, and you can load a new stylesheet with ``colors.load_stylesheet(...)``.


Recreating and loading the default stylesheet would look like this:

.. code-block:: python

    >>> default_styles = dict(
    ...  warn="fg red",
    ...  title="fg cyan underline bold",
    ...  fatal="fg red bold",
    ...  highlight="bg yellow",
    ...  info="fg blue",
    ...  success="fg green")

    >>> colors.load_stylesheet(default_styles)
          
          

The ``colors.from_ansi(code)`` method allows
you to create a Style from any ansi sequence, even complex or combined ones.


Colors
^^^^^^

The ``colors.fg`` and ``colors.bg`` allow you to access and generate colors. Named foreground colors are available
directly as methods. The first 16 primary colors, ``black``, ``red``, ``green``, ``yellow``,
``blue``, ``magenta``, ``cyan``, etc, as well as ``reset``, are available. All 256 color
names are available, but do not populate directly, so that auto-completion
gives reasonable results. You can also access colors using strings and do ``colors.fg[string]``.
Capitalization, underscores, and spaces (for strings) will be ignored. 

You can also access colors numerically with ``colors.fg[n]`` for the extended 256 color codes.
``colors.fg.rgb(r,g,b)`` will create a color from an
input red, green, and blue values (integers from 0-255). ``colors.fg.rgb(code)`` will allow
you to input an html style hex sequence.

Anything you can access from ``colors.fg`` can also be accessed directly from ``colors``.


256 Color Support
=================

While this library supports full 24 bit colors through escape sequences,
the library has special support for the "full" 256 colorset through numbers,
names or HEX html codes. Even if you use 24 bit color, the closest name is displayed
in the ``repr``. You can access the colors as
as ``colors.fg.Light_Blue``, ``colors.fg.lightblue``, ``colors.fg[12]``, ``colors.fg('Light_Blue')``,
``colors.fg('LightBlue')``, or ``colors.fg('#0000FF')``.
You can also iterate or slice the ``colors``, ``colors.fg``, or ``colors.bg`` objects. Slicing even
intelligently downgrades to the simple version of the codes if it is within the first 16 elements.
The supported colors are:

.. raw:: html
    :file: _color_list.html

If you want to enforce a specific representation, you can use ``.basic`` (8 color), ``.simple`` (16 color),
``.full`` (256 color), or ``.true`` (24 bit color) on a style, and the colors in that Style will conform to
the output representation and name of the best match color. The internal RGB colors
are remembered, so this is a non-destructive operation.

.. _guide-usecolors:

.. note::

    Some terminals only support a subset of colors, so keep this in mind when using a larger color set. The standard Ubuntu terminal handles 24 bit color, the Mac terminal only handles 256 colors, and Colorama on Windows only handles 8. See `this gist <https://gist.github.com/XVilka/8346728>`_ for information about support in terminals.
    If you need to limit the output color, you can set ``colors.use_color`` to
    0 (no colors), 1 (8 colors), 2 (16 colors), or 3 (256 colors), or 4 (24-bit colors). This option will be
    automatically guessed for you on initialization.


Style manipulations
===================

Safe color manipulations refer to changes that reset themselves at some point. Unsafe manipulations
must be manually reset, and can leave your terminal color in an unreadable state if you forget
to reset the color or encounter an exception. The library is smart and will try to restore the color
when Python exits.

.. note::

    If you do get the color unset on a terminal, the
    following, typed into the command line, will restore it:

    .. code:: bash

        $ python -m plumbum.colors

    This also supports command line access to unsafe color manipulations, such as

    .. code:: bash

        $ python -m plumbum.colors blue
        $ python -m plumbum.colors bg red
        $ python -m plumbum.colors fg 123
        $ python -m plumbum.colors bg reset
        $ python -m plumbum.colors underline

You can use any path or number available as a style.

Unsafe Manipulation
^^^^^^^^^^^^^^^^^^^

Styles have two unsafe operations: Concatenation (with ``+`` and a string) and calling ``.now()`` without
arguments (directly calling a style without arguments is also a shortcut for ``.now()``). These two
operations do not restore normal color to the terminal by themselves. To protect their use,
you can use a context manager around any unsafe operation.

An example of the usage of unsafe ``colors`` manipulations inside a context manager::

    from plumbum import colors

    with colors:
        colors.fg.red.now()
        print('This is in red')  .. raw:: html
    
    <p><font color="#800000">This is in red</font><br/>
    <font color="#008000">This is in green <span style="text-decoration: underline;">and now also underlined!</span></font><br/>
    <font color="#008000"><span style="text-decoration: underline;">Underlined</span> and not underlined but still green.</font><br/>
    This is completly restored, even if an exception is thrown! </p>

        colors.green.now()
        print('This is green ' + colors.underline + 'and now also underlined!')
        print('Underlined' + colors.underline.reset + ' and not underlined but still red') 
    print('This is completly restored, even if an exception is thrown!')

Output:

  .. raw:: html
    
    <p><font color="#800000">This is in red</font><br/>
    <font color="#008000">This is in green <span style="text-decoration: underline;">and now also underlined!</span></font><br/>
    <font color="#008000"><span style="text-decoration: underline;">Underlined</span> and not underlined but still green.</font><br/>
    This is completly restored, even if an exception is thrown! </p>

We can use ``colors`` instead of ``colors.fg`` for foreground colors.  If we had used ``colors.fg``
as the context manager, then non-foreground properties, such as ``colors.underline`` or
``colors.bg.yellow``, would not have been reset. Each attribute,
as well as ``fg``, ``bg``, and ``colors`` all have inverses in the ANSI standard. They are
accessed with ``~``  or ``.reset``, and can be used to manually make these operations
safer, but there is a better way.

Safe Manipulation
^^^^^^^^^^^^^^^^^

All other operations are safe; they restore the color automatically. The first, and hopefully
already obvious one, is using a specific style rather than a ``colors`` or ``colors.fg`` object in a ``with`` statement.
This will set the color (using ``sys.stdout`` by default) to that color, and restore color on leaving.

The second method is to manually wrap a string. This can be done with ``color | "string"`` or ``color["string"]``.
These produce strings that can be further manipulated or printed.

Finally, you can also print a color to stdout directly using
``color.print("string")``. This
has the same syntax as the Python 3 print function. In Python 2, if you do not have
``from __future__ import print_function`` enabled, ``color.print_("string")`` is provided as
an alternative, following the PyQT convention for method names that match reserved Python syntax.

An example of safe manipulations::

    colors.fg.yellow('This is yellow', end='')
    print(' And this is normal again.')
    with colors.red:
        print('Red color!')
        with colors.bold:
            print("This is red and bold.")
        print("Not bold, but still red.")
    print("Not red color or bold.")
    print(colors.magenta & colors.bold | "This is bold and colorful!", "And this is not.")

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

You can combine styles with ``&`` and they will create a new combined style. Colors will not be "summed"
or otherwise combined; the rightmost color will be used (this matches the expected effect of
applying the styles individually to the strings). However, combined styles are intelligent and
know how to reset just the properties that they contain. As you have seen in the example above,
the combined style ``(colors.magenta & colors.bold)`` can be used in any way a normal style can.


New color systems
=================

The library was written primarily for ANSI color sequences, but can also easily be subclassed to create new color
systems. See :ref:`guide-colorlib` for information on how the system works. An HTML version is available as
``plumbum.colorlib.htmlcolors``.

See Also
========

* `colored <https://pypi.python.org/pypi/colored>`_ Another library with 256 color support
* `colorama <https://pypi.python.org/pypi/colorama>`_ A library that supports colored text on Windows,
    can be combined with Plumbum.colors (if you force ``use_color``, doesn't support all extended colors)
