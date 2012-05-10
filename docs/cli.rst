.. _guide-cli:

Command-Line Interface (CLI)
============================

The other side of *executing programs* with ease is **writing CLI programs** with ease. 
Python scripts normally use ``optparse`` or the more recent ``argparse``, and their 
`derivatives <http://packages.python.org/argh/index.html>`_; but all of these are somewhat 
limited in their expressive power, and are quite **unintuitive** (and even **unpythonic**).
Plumbum's CLI toolkit offers a **programmatic approach** to building command-line applications;
instead of creating a parser object and populating it with a series of "options", the CLI toolkit
translates these primitives into Pythonic constructs and relies on introspection.

From a bird's eye view, CLI applications are classes that extend :class:`plumbum.cli.Application`.
They define a ``main()`` method and optionally expose methods and attributes as command-line
:func:`switches <plumbum.cli.switch>`. Switches may take arguments, and any remaining positional 
arguments are given to the ``main`` method, according to its signature. A simple CLI application
might look like this::

    from plumbum import cli
    
    class MyApp(cli.Application):
        verbose = cli.Flag(["v", "verbose"], help = "If given, I will be very talkative")
        
        def main(self, filename):
            print "I will now read", filename
            if self.verbose:
                print "Yadda " * 200
    
    if __name__ == "__main__":
        MyApp.run()

And you can run it::

    $ python example.py foo
    I will now read foo
    
    $ python example.py --help
    example.py v1.0
    
    Usage: example.py [SWITCHES] filename
    Meta-switches:
        -h, --help                 Prints this help message and quits
        --version                  Prints the program's version and quits
    
    Switches:
        -v, --verbose              If given, I will be very talkative

So far you've only seen the very basic usage. We'll now start to explore the library.


Application
-----------
The :class:`Application <plumbum.cli.Application>` class is the "container" of your application.
It consists of the ``main()`` method, which you should implement, and any number of CLI-exposed
switch functions or attributes. The entry-point for your application is the classmethod ``run``,
which instantiates your class, parses the arguments, invokes all switch functions, and then
calls ``main()`` with the given positional arguments. In order to run your application from the
command-line, all you have to do is ::

    if __name__ == "__main__":
        MyApp.run()

Aside from ``run()`` and ``main()``, the ``Application`` class exposes two built-in switch 
functions: ``help()`` and ``version()`` which take care of displaying the help and program's
version, respectively. By default, ``--help`` and ``-h`` invoke ``help()``, and ``--version`` 
and ``-v`` invoke ``version()``; if any of these functions is called, the application will display
the message and quit (without processing any other switch).

You can customize the information displayed by ``help()`` and ``version`` by defining 
class-level attributes, such as ``PROGNAME``, ``VERSION`` and ``DESCRIPTION``. For instance, ::

    class MyApp(cli.Application):
        PROGNAME = "Foobar"
        VERSION = "7.3"

Switch Functions
----------------
The decorator :func:`switch <plumbum.cli.switch>` can be seen as the "heart and soul" of the 
CLI toolkit; it exposes methods of your CLI application as CLI-switches, allowing them to be
invoked from the command line. Let's examine the following toy application::

    class MyApp(cli.Application):
        @switch("--log-to-file", str)
        def log_to_file(self, filename):
            """Sets the file into which logs will be emitted"""
            logger.addHandler(FileHandle(filename))
    
        @switch(["-r", "--root"])
        def allow_as_root(self):
            """If given, allow running as root"""
            self._allow_root = True
    
        def main(self):
            if os.geteuid() == 0 and not self._allow_root:
                raise ValueError("cannot run as root")

When the program is run, the switch functions are invoked with their appropriate arguments;
for instance, ``$ ./myapp.py --log-to-file=/tmp/log`` would translate to a call to 
``app.log_to_file("/tmp/log")``. After all switches were processed, control passes to ``main``.

.. note::
    Methods' docstrings and argument names will be used to render the help message, keeping your
    code as `DRY <http://en.wikipedia.org/wiki/Don't_repeat_yourself>`_ as possible

Arguments
^^^^^^^^^
As seen in the example above, switch functions may take a single argument. 

* Range
* Set

List
^^^^

Mandatory Switches
^^^^^^^^^^^^^^^^^^

Dependencies
^^^^^^^^^^^^

Mutual Exclusion
^^^^^^^^^^^^^^^^^

Grouping
^^^^^^^^

Switch Attributes
-----------------
* SwitchAttr
* Flag
* CountAttr

Main
----

* arguments
* varargs








