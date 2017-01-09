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
            print("I will now read {0}".format(filename))
            if self.verbose:
                print("Yadda " * 200)
    
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

.. versionadded:: 1.6.1

    You can also directly run the app, as ``MyApp()``, without arguments, instead of calling ``.main()``.

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

Colors
^^^^^^
.. versionadded:: 1.6
       
Colors are supported. You can use a colored string on ``PROGNAME``, ``VERSION`` and ``DESCRIPTION`` directly.
If you set ``PROGNAME`` to a color, you can get auto-naming and color.
The color of the usage string is available as ``COLOR_USAGE``, and the different groups can be colored with a
dictionary ``COLOR_GROUPS``.

For instance, the following is valid::

    class MyApp(cli.Application):
        PROGNAME = colors.green
        VERSION = colors.blue | "1.0.2"
        COLOR_GROUPS = {"Meta-switches" : colors.bold & colors.yellow}
        opts =  cli.Flag("--ops", help=colors.magenta | "This is help")



.. raw:: html

    <pre>
    <font color="#00C000">SimpleColorCLI.py</font> <font color="#0000C0">1.0.2</font>
    
    Usage:
        <font color="#00C000">SimpleColorCLI.py</font> [SWITCHES] 

    <font color="#C0C000"><b>Meta-switches</b></font>
        <font color="#C0C000"><b>-h, --help</b></font>         <font color="#C0C000"><b>Prints this help message and quits</b></font>
        <font color="#C0C000"><b>--help-all</b></font>         <font color="#C0C000"><b>Print help messages of all subcommands and quit</b></font>
        <font color="#C0C000"><b>-v, --version</b></font>      <font color="#C0C000"><b>Prints the program's version and quits</b></font>

    Switches
        --ops              <font color="#C000C0">This is help</font>
    </pre>



Switch Functions
----------------
The decorator :func:`switch <plumbum.cli.switch>` can be seen as the "heart and soul" of the 
CLI toolkit; it exposes methods of your CLI application as CLI-switches, allowing them to be
invoked from the command line. Let's examine the following toy application::

    class MyApp(cli.Application):
        _allow_root = False       # provide a default

        @cli.switch("--log-to-file", str)
        def log_to_file(self, filename):
            """Sets the file into which logs will be emitted"""
            logger.addHandler(FileHandle(filename))
    
        @cli.switch(["-r", "--root"])
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
   code as `DRY <http://en.wikipedia.org/wiki/Don't_repeat_yourself>`_ as possible.
   
   There's also :func:`autoswitch <plumbum.cli.autoswitch>`, which infers the name of the switch
   from the function's name, e.g. ::
        
        @cli.autoswitch(str)
        def log_to_file(self, filename):
            pass
   
   Will bind the switch function to ``--log-to-file``.

Arguments
^^^^^^^^^
As demonstrated in the example above, switch functions may take no arguments (not counting 
``self``) or a single argument argument. If a switch function accepts an argument, it must 
specify the argument's *type*. If you require no special validation, simply pass ``str``; 
otherwise, you may pass any type (or any callable, in fact) that will take a string and convert 
it to a meaningful object. If conversion is not possible, the type (or callable) is expected to
raise either ``TypeError`` or ``ValueError``.

For instance ::

    class MyApp(cli.Application):
        _port = 8080
        
        @cli.switch(["-p"], int)
        def server_port(self, port):
            self._port = port
        
        def main(self):
            print(self._port)

::

    $ ./example.py -p 17
    17
    $ ./example.py -p foo
    Argument of -p expected to be <type 'int'>, not 'foo':
        ValueError("invalid literal for int() with base 10: 'foo'",)    

The toolkit includes two additional "types" (or rather, *validators*): ``Range`` and ``Set``.
``Range`` takes a minimal value and a maximal value and expects an integer in that range 
(inclusive). ``Set`` takes a set of allowed values, and expects the argument to match one of 
these values. Here's an example ::  

    class MyApp(cli.Application):
        _port = 8080
        _mode = "TCP"
        
        @cli.switch("-p", cli.Range(1024,65535))
        def server_port(self, port):
            self._port = port
        
        @cli.switch("-m", cli.Set("TCP", "UDP", case_sensitive = False))
        def server_mode(self, mode):
            self._mode = mode
        
        def main(self):
            print(self._port, self._mode)

::

    $ ./example.py -p 17
    Argument of -p expected to be [1024..65535], not '17':
        ValueError('Not in range [1024..65535]',)
    $ ./example.py -m foo
    Argument of -m expected to be Set('udp', 'tcp'), not 'foo':
        ValueError("Expected one of ['UDP', 'TCP']",)

.. note::
   The toolkit also provides some other useful validators: `ExistingFile` (ensures the given 
   argument is an existing file), `ExistingDirectory` (ensures the given argument is an existing 
   directory), and `NonexistentPath` (ensures the given argument is not an existing path).
   All of these convert the argument to a :ref:`local path <guide-paths>`.


Repeatable Switches
^^^^^^^^^^^^^^^^^^^
Many times, you would like to allow a certain switch to be given multiple times. For instance,
in ``gcc``, you may give several include directories using ``-I``. By default, switches may
only be given once, unless you allow multiple occurrences by passing ``list = True`` to the
``switch`` decorator ::

    class MyApp(cli.Application):
        _dirs = []
        
        @cli.switch("-I", str, list = True)
        def include_dirs(self, dirs):
            self._dirs = dirs
        
        def main(self):
            print(self._dirs)

::

    $ ./example.py -I/foo/bar -I/usr/include
    ['/foo/bar', '/usr/include']

.. note::
   The switch function will be called **only once**, and its argument will be a list of items

Mandatory Switches
^^^^^^^^^^^^^^^^^^
If a certain switch is required, you can specify this by passing ``mandatory = True`` to the 
``switch`` decorator. The user will not be able to run the program without specifying a value
for this switch.

Dependencies
^^^^^^^^^^^^
Many time, the occurrence of a certain switch depends on the occurrence of another, e..g, it 
may not be possible to give ``-x`` without also giving ``-y``. This constraint can be achieved
by specifying the ``requires`` keyword argument to the ``switch`` decorator; it is a list
of switch names that this switch depends on. If the required switches are missing, the user
will not be able to run the program. :: 

    class MyApp(cli.Application):
        @cli.switch("--log-to-file", str)
        def log_to_file(self, filename):
            logger.addHandler(logging.FileHandler(filename))
    
        @cli.switch("--verbose", requires = ["--log-to-file"])
        def verbose(self):
            logger.setLevel(logging.DEBUG)

::

    $ ./example --verbose
    Given --verbose, the following are missing ['log-to-file']

.. warning::
   The toolkit invokes the switch functions in the same order in which the switches were given
   on the command line. It doesn't go as far as computing a topological order on the fly, but
   this will change in the future.

Mutual Exclusion
^^^^^^^^^^^^^^^^^
Just as some switches may depend on others, some switches mutually-exclude others. For instance,
it does not make sense to allow ``--verbose`` and ``--terse``. For this purpose, you can set the
``excludes`` list in the ``switch`` decorator. ::

    class MyApp(cli.Application):
        @cli.switch("--log-to-file", str)
        def log_to_file(self, filename):
            logger.addHandler(logging.FileHandler(filename))
    
        @cli.switch("--verbose", requires = ["--log-to-file"], excludes = ["--terse"])
        def verbose(self):
            logger.setLevel(logging.DEBUG)
        
        @cli.switch("--terse", requires = ["--log-to-file"], excludes = ["--verbose"])
        def terse(self):
            logger.setLevel(logging.WARNING)

::

    $ ./example --log-to-file=log.txt --verbose --terse
    Given --verbose, the following are invalid ['--terse']

Grouping
^^^^^^^^
If you wish to group certain switches together in the help message, you can specify 
``group = "Group Name"``, where ``Group Name`` is any string. When the help message is rendered,
all the switches that belong to the same group will be grouped together. Note that grouping has
no other effects on the way switches are processed, but it can help improve the readability of
the help message.

Switch Attributes
-----------------
Many times it's desired to simply store a switch's argument in an attribute, or set a flag if 
a certain switch is given. For this purpose, the toolkit provides 
:class:`SwitchAttr <plumbum.cli.SwitchAttr>`, which is `data descriptor 
<http://docs.python.org/howto/descriptor.html>`_ that stores the argument in an instance attribute.
There are two additional "flavors" of ``SwitchAttr``: ``Flag`` (which toggles its default value
if the switch is given) and ``CountOf`` (which counts the number of occurrences of the switch)
::

    class MyApp(cli.Application):
        log_file = cli.SwitchAttr("--log-file", str, default = None)
        enable_logging = cli.Flag("--no-log", default = True)
        verbosity_level = cli.CountOf("-v")
        
        def main(self):
            print(self.log_file, self.enable_logging, self.verbosity_level)

.. code-block:: bash

    $ ./example.py -v --log-file=log.txt -v --no-log -vvv
    log.txt False 5


Environment Variables
^^^^^^^^^^^^^^^^^^^^^
.. versionadded:: 1.6

You can also set a ``SwitchAttr`` to take an environment variable as an input using the envname parameter.
For example::

    class MyApp(cli.Application):
        log_file = cli.SwitchAttr("--log-file", str, envname="MY_LOG_FILE")

        def main(self):
            print(self.log_file)

.. code-block:: bash

    $ MY_LOG_FILE=this.log ./example.py
    this.log

Giving the switch on the command line will override the environment variable value.

    

Main
----

The ``main()`` method takes control once all the command-line switches have been processed.
It may take any number of *positional argument*; for instance, in ``cp -r /foo /bar``,
``/foo`` and ``/bar`` are the *positional arguments*. The number of positional arguments
that the program would accept depends on the signature of the method: if the method takes 5 
arguments, 2 of which have default values, then at least 3 positional arguments must be supplied
by the user and at most 5. If the method also takes varargs (``*args``), the number of
arguments that may be given is unbound ::

    class MyApp(cli.Application):
        def main(self, src, dst, mode = "normal"):
            print(src, dst, mode)

::

    $ ./example.py /foo /bar
    /foo /bar normal
    $ ./example.py /foo /bar spam
    /foo /bar spam
    $ ./example.py /foo
    Expected at least 2 positional arguments, got ['/foo']
    $ ./example.py /foo /bar spam bacon
    Expected at most 3 positional arguments, got ['/foo', '/bar', 'spam', 'bacon']

.. note::
   The method's signature is also used to generate the help message, e.g. ::
    
        Usage:  [SWITCHES] src dst [mode='normal']

With varargs::

    class MyApp(cli.Application):
        def main(self, src, dst, *eggs):
            print(src, dst, eggs)

::

    $ ./example.py a b c d
    a b ('c', 'd')
    $ ./example.py --help
    Usage:  [SWITCHES] src dst eggs...
    Meta-switches:
        -h, --help                 Prints this help message and quits
        -v, --version              Prints the program's version and quits

Positional argument validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. versionadded:: 1.6

You can supply positional argument validators using the ``cli.positional`` decorator. Simply
pass the validators in the decorator matching the names in the main function. For example::

    class MyApp(cli.Application):
        @cli.positional(cli.ExistingFile, cli.NonexistentPath)
        def main(self, infile, *outfiles):
            "infile is a path, outfiles are a list of paths, proper errors are given"

If you only want to run your application in Python 3, you can also use annotations to
specify the validators. For example::

    class MyApp(cli.Application):
        def main(self, infile : cli.ExistingFile, *outfiles : cli.NonexistentPath):
        "Identical to above MyApp"

Annotations are ignored if the positional decorator is present.
    


.. _guide-subcommands:


Sub-commands
------------
.. versionadded:: 1.1

A common practice of CLI applications, as they span out and get larger, is to split their
logic into multiple, pluggable *sub-applications* (or *sub-commands*). A classic example is version
control systems, such as `git <http://git-scm.com/>`_, where ``git`` is the *root* command, 
under which sub-commands such as ``commit`` or ``push`` are nested. Git even supports ``alias``-ing,
which creates allows users to create custom sub-commands. Plumbum makes writing such applications 
really easy.

Before we get to the code, it is important to stress out two things:

* Under Plumbum, each sub-command is a full-fledged ``cli.Application`` on its own; if you wish,
  you can execute it separately, detached from its so-called root application. When an application
  is run independently, its ``parent`` attribute is ``None``; when it is run as a sub-command, 
  its ``parent`` attribute points to its parent application. Likewise, when an parent application 
  is executed with a sub-command, its ``nested_command`` is set to the nested application; otherwise
  it's ``None``.

* Each sub-command is responsible of **all** arguments that follow it (up to the next sub-command). 
  This allows applications to process their own switches and positional arguments before the nested
  application is invoked. Take, for instance, ``git --foo=bar spam push origin --tags``: the root
  application, ``git``, is in charge of the switch ``--foo`` and the positional argument ``spam``,
  and the nested application ``push`` is in charge of the arguments that follow it. In theory, 
  you can nest several sub-applications one into the other; in practice, only a single level
  is normally used.

Here is an example of a mock version control system, called ``geet``. We're going to have a root
application ``Geet``, which has two sub-commands - ``GeetCommit`` and ``GeetPush``: these are 
attached to the root application using the ``subcommand`` decorator ::
    
    class Geet(cli.Application):
        """The l33t version control"""
        VERSION = "1.7.2"
        
        def main(self, *args):
            if args:
                print("Unknown command {0!r}".format(args[0]))
                return 1   # error exit code
            if not self.nested_command:           # will be ``None`` if no sub-command follows
                print("No command given")
                return 1   # error exit code

    @Geet.subcommand("commit")                    # attach 'geet commit'
    class GeetCommit(cli.Application):
        """creates a new commit in the current branch"""
        
        auto_add = cli.Flag("-a", help = "automatically add changed files")
        message = cli.SwitchAttr("-m", str, mandatory = True, help = "sets the commit message")

        def main(self):
            print("doing the commit...")

    @Geet.subcommand("push")                      # attach 'geet push'
    class GeetPush(cli.Application):
        """pushes the current local branch to the remote one"""
        def main(self, remote, branch = None):
            print("doing the push...")

    if __name__ == "__main__":
        Geet.run()

.. note::
    * Since ``GeetCommit`` is a ``cli.Application`` on its own right, you may invoke 
      ``GeetCommit.run()`` directly (should that make sense in the context of your application)
    * You can also attach sub-commands "imperatively", using ``subcommand`` as a method instead
      of a decorator: ``Geet.subcommand("push", GeetPush)``

Here's an example of running this application::

    $ python geet.py --help
    geet v1.7.2
    The l33t version control
    
    Usage: geet.py [SWITCHES] [SUBCOMMAND [SWITCHES]] args...
    Meta-switches:
        -h, --help                 Prints this help message and quits
        -v, --version              Prints the program's version and quits
    
    Subcommands:
        commit                     creates a new commit in the current branch; see
                                   'geet commit --help' for more info
        push                       pushes the current local branch to the remote
                                   one; see 'geet push --help' for more info
    
    $ python geet.py commit --help
    geet commit v1.7.2
    creates a new commit in the current branch
    
    Usage: geet commit [SWITCHES]
    Meta-switches:
        -h, --help                 Prints this help message and quits
        -v, --version              Prints the program's version and quits
    
    Switches:
        -a                         automatically add changed files
        -m VALUE:str               sets the commit message; required
    
    $ python geet.py commit -m "foo"
    committing...


Configuration parser
--------------------

Another common task of a cli application is provided by a configuration parser, with an INI backend: ``Config`` (or ``ConfigINI`` to explicitly request the INI backend). An example of it's use::

    from plumbum import cli

    with cli.Config('~/.myapp_rc') as conf:
        one = conf.get('one', '1')
        two = conf.get('two', '2')

If no configuration file is present, this will create one and each call to ``.get`` will set the value with the given default.
The file is created when the context manager exits.
If the file is present, it is read and the values from the file are selected, and nothing is changed.
You can also use ``[]`` syntax to forcably set a value, or to get a value with a standard ``ValueError`` if not present.
If you want to avoid the context manager, you can use ``.read`` and ``.write`` as well.

The ini parser will default to using the ``[DEFAULT]`` section for values, just like Python's ConfigParser on which it is based. If you want to use a different section, simply seperate section and heading with a ``.`` in the key. ``conf['section.item']`` would place ``item`` under ``[section]``. All items stored in an ``ConfigINI`` are converted to ``str``, and ``str`` is always returned.

Terminal Utilities
------------------

Several terminal utilities are available in ``plumbum.cli.terminal`` to assist in making terminal
applications.

``get_terminal_size(default=(80,25))`` allows cross platform access to the terminal size as a tuple ``(width, height)``.
Several methods to ask the user for input, such as ``readline``, ``ask``, ``choose``, and ``prompt`` are available.

``Progress(iterator)`` allows you to quickly create a progress bar from an iterator. Simply wrap a slow iterator with this
and iterate over it, and it will produce a nice text progress bar based on the user's screen width, with estimated time
remaining displayed. If you need to create a progress bar for a fast iterator but with a loop containing code, use ``Progress.wrap`` or ``Progress.range``. For example::

    for i in Progress.range(10):
        time.sleep(1)

If you have something that produces output, but still needs a progress bar, pass ``has_output=True`` to force the bar not to try to erase the old one each time.

A command line image plotter (``Image``) is provided in ``plumbum.cli.image``. It can plot a PIL-like image ``im`` using::

    Image().show_pil(im)

The Image constructor can take an optional size (defaults to the current terminal size if None), and a `char_ratio`, a height to width measure for your current font. It defaults to a common value of 2.45. If set to None, the ratio is ignored and the image will no longer be constrained to scale proportionately. To directly plot an image, the ``show`` method takes a filename and a double parameter, which doubles the vertical resolution on some fonts. The `show_pil` and `show_pil_double`
methods directly take a PIL-like object. To plot an image from the command line,  
the module can be run directly: ``python -m plumbum.cli.image myimage.png``.

For the full list of helpers or more information, see the :ref:`api docs <api-cli>`.



See Also
--------
* `filecopy.py <https://github.com/tomerfiliba/plumbum/blob/master/examples/filecopy.py>`_ example
* `geet.py <https://github.com/tomerfiliba/plumbum/blob/master/examples/geet.py>`_ - a runnable 
  example of using sub-commands
* `RPyC <http://rpyc.sf.net>`_ has changed it bash-based build script to Plumbum CLI.
  Notice `how short and readable <https://github.com/tomerfiliba/rpyc/blob/c457a28d689df7605838334a437c6b35f9a94618/build.py>`_
  it is.
* A `blog post <http://tomerfiliba.com/blog/Plumbum/>`_ describing the philosophy of the CLI module



