.. _guide-colorlib:

Colorlib design
---------------

.. versionadded:: 1.6


The purpose of this document is to describe the system
that plumbum.colors implements. This system was designed to be flexible and
to allow implementing new color backends. Hopefully this document will allow
future work on colorlib to be as simple as possible.

.. note:: Enabling color

    ``plumbum.colors`` tries to guess the color output settings of your system.
    You can force the use of color globally by setting
    ``colors.use_color=True`` See :ref:`guide-colorlist` for more options.

Generating colors
=================

Styles are accessed through the ``colors`` object, which is an instance of a StyleFactory. The ``colors``
object is actually an imitation module that wraps ``plumbum.colorlib.ansicolors`` with module-like access.
Thus, things like from ``plumbum.colors.bg import red`` work also. The library actually lives in ``plumbum.colorlib``.


Style Factory
^^^^^^^^^^^^^

The ``colors`` object has the following available objects:

    ``fg`` and ``bg``
      The foreground and background colors, reset to default with ``colors.fg.reset``
      or ``~colors.fg`` and likewise for ``bg``. These are ``ColorFactory`` instances.
    ``bold``, ``dim``, ``underline``, ``italics``, ``reverse``, ``strikeout``, and ``hidden``
      All the `ANSI` modifiers are available, as well as their negations, such
      as ``~colors.bold`` or ``colors.bold.reset``, etc. (These are generated automatically
      based on the Style attached to the factory.)
    ``reset``
      The global reset will restore all properties at once.
    ``do_nothing``
      Does nothing at all, but otherwise acts like any ``Style`` object. It is its own inverse. Useful for ``cli`` properties.

The ``colors`` object can be used in a with statement, which resets all styles on leaving 
the statement body. Although factories do support
some of the same methods as a Style, their primary purpose is to generate Styles. The colors object has a
``use_color`` property that can be set to force the use of color. A ``stdout`` property is provided
to make changing the output of color statement easier. A ``colors.from_ansi(code)`` method allows
you to create a Style from any ansi sequence, even complex or combined ones.

Color Factories
^^^^^^^^^^^^^^^

The ``colors.fg`` and ``colors.bg`` are ``ColorFactory``'s. In fact, the colors object itself acts exactly
like the ``colors.fg`` object, with the exception of the properties listed above.

Named foreground colors are available
directly as methods. The first 16 primary colors, ``black``, ``red``, ``green``, ``yellow``,
``blue``, ``magenta``, ``cyan``, etc, as well as ``reset``, are available. All 256 color
names are available, but do not populate factory directly, so that auto-completion
gives reasonable results. You can also access colors using strings and do ``colors[string]``.
Capitalization, underscores, and spaces (for strings) will be ignored.

You can also access colors numerically with ``colors(n)`` or  ``colors[n]``
with the extended 256 color codes. The former will default to simple versions of
colors for the first 16 values. The later notation can also be used to slice.
Full hex codes can be used, too. If no match is found,
these will be the true 24 bit color value.

The ``fg`` and ``bg`` also can be put in with statements, and they
will restore the foreground and background color only, respectively. 

``colors.rgb(r,g,b)`` will create a color from an
input red, green, and blue values (integers from 0-255). ``colors.rgb(code)`` will allow
you to input an html style hex sequence. These work on ``fg`` and ``bg`` too. The ``repr`` of
styles is smart and will show you the closest color to the one you selected if you didn't exactly
select a color through RGB. 

Style manipulations
===================

Safe color manipulations refer to changes that reset themselves at some point. Unsafe manipulations
must be manually reset, and can leave your terminal color in an unreadable state if you forget
to reset the color or encounter an exception. If you do get the color unset on a terminal, the
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
you should always use a context manager around any unsafe operation.

An example of the usage of unsafe ``colors`` manipulations inside a context manager::

    from plumbum import colors

    with colors:
        colors.fg.red.now()
        print('This is in red')
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
``colors.bg.yellow``, would not have reset those properties. Each attribute,
as well as ``fg``, ``bg``, and ``colors`` all have inverses in the ANSI standard. They are
accessed with ``~``  or ``.reset``, and can be used to manually make these operations
safer, but there is a better way.

Safe Manipulation
^^^^^^^^^^^^^^^^^

All other operations are safe; they restore the color automatically. The first, and hopefully
already obvious one, is using a Style rather than a ``colors`` or ``colors.fg`` object in a ``with`` statement.
This will set the color (using sys.stdout by default) to that color, and restore color on leaving.

The second method is to manually wrap a string. This can be done with ``color.wrap("string")`` or ``color["string"]``.
These produce strings that can be further manipulated or printed.


Finally, you can also print a color to stdout directly using ``color.print("string")``. This
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
    print((colors.magenta & colors.bold)["This is bold and colorful!"], "And this is not.")

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

You can combine styles with ``&`` and they will create a new combined Style object. Colors will not be "summed"
or otherwise combined; the rightmost color will be used (this matches the expected effect of
applying the Styles individually to the strings). However, combined Styles are intelligent and
know how to reset just the properties that they contain. As you have seen in the example above,
the combined style ``(colors.magenta & colors.bold)`` can be used in any way a normal Style can.
Since wrapping is done with ``|``, the Python order of operations causes styles to be combined first, then
wrapping is done last.

.. _guide-colorlist:

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
``.full`` (256 color), or ``.true`` (24 bit color) on a Style, and the colors in that Style will conform to
the output representation and name of the best match color. The internal RGB colors
are remembered, so this is a non-destructive operation.

To limit the use of color to one of these styles, set ``colors.use_color`` to 1 for 8 colors, 2 for 16 colors, 
3 for 256 colors, or 4 for true color. It will be guessed based on your system on initialisation.

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
by the ``colors`` factory. It holds ``Color`` as ``.color_class``, which can be overridden by subclasses (again, this usually is not needed).
To create a color representation, you need to subclass ``Style`` and give it a working ``__str__`` definition. ``ANSIStyle`` is derived
from ``Style`` in this way.

The factories, ``ColorFactory`` and ``StyleFactory``, are factory classes that are meant to provide simple access to 1 style Style classes. To use,
you need to initialize an object of ``StyleFactory`` with your intended Style. For example, ``colors`` is created by::

    colors = StyleFactory(ANSIStyle)

Subclassing Style
^^^^^^^^^^^^^^^^^

For example, if you wanted to create an HTMLStyle and HTMLcolors, you could do::

    class HTMLStyle(Style):
        attribute_names = dict(bold='b', li='li', code='code')
        end = '<br/>\n'

        def __str__(self):
            result = ''

            if self.bg and not self.bg.reset:
                result += '<span style="background-color: {0}">'.format(self.bg.hex_code)
            if self.fg and not self.fg.reset:
                result += '<font color="{0}">'.format(self.fg.hex_code)
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

    htmlcolors = StyleFactory(HTMLStyle)
    
This doesn't support global resets, since that's not how HTML works, but otherwise is a working implementation. This is an example of how easy it is to add support for other output formats.

An example of usage::

    >>>  htmlcolors.bold & htmlcolors.red | "This is colored text"
    '<font color="#800000"><b>This is colored text</b></font>'


The above color table can be generated with::

    for color in htmlcolors:
        htmlcolors.li(
            "&#x25a0;" | color,
            color.fg.hex_code | htmlcolors.code,
            color.fg.name_camelcase)


.. note::
    
    ``HTMLStyle`` is implemented in the library, as well, with the
    ``htmlcolors`` object available in ``plumbum.colorlib``. It was used
    to create the colored output in this document, with small changes
    because ``colors.reset`` cannot be supported with HTML.

See Also
========

* `colored <https://pypi.python.org/pypi/colored>`_ Another library with 256 color support
* `colorama <https://pypi.python.org/pypi/colorama>`_ A library that supports colored text on Windows,
    can be combined with Plumbum.colors (if you force ``use_color``, doesn't support all extended colors)
