.. image:: https://readthedocs.org/projects/plumbum/badge/
   :target: https://plumbum.readthedocs.io/en/latest/
   :alt: Documentation Status
.. image:: https://github.com/tomerfiliba/plumbum/workflows/CI/badge.svg
   :target: https://github.com/tomerfiliba/plumbum/actions
   :alt: Build Status
.. image:: https://coveralls.io/repos/tomerfiliba/plumbum/badge.svg?branch=master&service=github
   :target: https://coveralls.io/github/tomerfiliba/plumbum?branch=master
   :alt: Coverage Status
.. image:: https://img.shields.io/pypi/v/plumbum.svg
   :target: https://pypi.python.org/pypi/plumbum/
   :alt: PyPI Status
.. image:: https://img.shields.io/pypi/pyversions/plumbum.svg
   :target: https://pypi.python.org/pypi/plumbum/
   :alt: PyPI Versions
.. image:: https://img.shields.io/conda/vn/conda-forge/plumbum.svg
   :target: https://github.com/conda-forge/plumbum-feedstock
   :alt: Conda-Forge Badge
.. image:: https://img.shields.io/pypi/l/plumbum.svg
   :target: https://pypi.python.org/pypi/plumbum/
   :alt: PyPI License
.. image:: https://badges.gitter.im/plumbumpy/Lobby.svg
   :alt: Join the chat at https://gitter.im/plumbumpy/Lobby
   :target: https://gitter.im/plumbumpy/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :alt: Code styled with Black
   :target: https://github.com/psf/black


Plumbum: Shell Combinators
==========================

Ever wished the compactness of shell scripts be put into a **real** programming language?
Say hello to *Plumbum Shell Combinators*. Plumbum (Latin for *lead*, which was used to create
pipes back in the day) is a small yet feature-rich library for shell script-like programs in Python.
The motto of the library is **"Never write shell scripts again"**, and thus it attempts to mimic
the **shell syntax** ("shell combinators") where it makes sense, while keeping it all **Pythonic
and cross-platform**.

Apart from shell-like syntax and handy shortcuts, the library provides local and remote command
execution (over SSH), local and remote file-system paths, easy working-directory and environment
manipulation, and a programmatic Command-Line Interface (CLI) application toolkit.
Now let's see some code!

*This is only a teaser; the full documentation can be found at*
`Read the Docs <https://plumbum.readthedocs.io>`_

Cheat Sheet
-----------

Basics
******

.. code-block:: python

    >>> from plumbum import local
    >>> local.cmd.ls
    LocalCommand(/bin/ls)
    >>> local.cmd.ls()
    'build.py\nCHANGELOG.rst\nconda.recipe\nCONTRIBUTING.rst\ndocs\nexamples\nexperiments\nLICENSE\nMANIFEST.in\nPipfile\nplumbum\nplumbum.egg-info\npytest.ini\nREADME.rst\nsetup.cfg\nsetup.py\ntests\ntranslations.py\n'
    >>> notepad = local["c:\\windows\\notepad.exe"]
    >>> notepad()                                   # Notepad window pops up
    ''                                              # Notepad window is closed by user, command returns

In the example above, you can use ``local["ls"]`` if you have an unusually named executable or a full path to an executable. The ``local`` object represents your local machine. As you'll see, Plumbum also provides remote machines that use the same API!
You can also use ``from plumbum.cmd import ls`` as well for accessing programs in the ``PATH``.

Piping
******

.. code-block:: python

    >>> from plumbum.cmd import ls, grep, wc
    >>> chain = ls["-a"] | grep["-v", r"\.py"] | wc["-l"]
    >>> print(chain)
    /bin/ls -a | /bin/grep -v '\.py' | /usr/bin/wc -l
    >>> chain()
    '27\n'

Redirection
***********

.. code-block:: python

    >>> from plumbum.cmd import cat, head
    >>> ((cat < "setup.py") | head["-n", 4])()
    '#!/usr/bin/env python3\nimport os\n\ntry:\n'
    >>> (ls["-a"] > "file.list")()
    ''
    >>> (cat["file.list"] | wc["-l"])()
    '31\n'

Working-directory manipulation
******************************

.. code-block:: python

    >>> local.cwd
    <LocalWorkdir /home/tomer/workspace/plumbum>
    >>> with local.cwd(local.cwd / "docs"):
    ...     chain()
    ...
    '22\n'

Foreground and background execution
***********************************

.. code-block:: python

    >>> from plumbum import FG, BG
    >>> (ls["-a"] | grep[r"\.py"]) & FG         # The output is printed to stdout directly
    build.py
    setup.py
    translations.py
    >>> (ls["-a"] | grep[r"\.py"]) & BG         # The process runs "in the background"
    <Future ['/bin/grep', '\\.py'] (running)>

Command nesting
***************

.. code-block:: python

    >>> from plumbum.cmd import sudo, ifconfig
    >>> print(sudo[ifconfig["-a"]])
    /usr/bin/sudo /sbin/ifconfig -a
    >>> (sudo[ifconfig["-a"]] | grep["-i", "loop"]) & FG
    lo        Link encap:Local Loopback
              UP LOOPBACK RUNNING  MTU:16436  Metric:1

Remote commands (over SSH)
**************************

Supports `openSSH <http://www.openssh.org/>`_-compatible clients,
`PuTTY <http://www.chiark.greenend.org.uk/~sgtatham/putty/>`_ (on Windows)
and `Paramiko <https://github.com/paramiko/paramiko/>`_ (a pure-Python implementation of SSH2)

.. code-block:: python

    >>> from plumbum import SshMachine
    >>> remote = SshMachine("somehost", user = "john", keyfile = "/path/to/idrsa")
    >>> r_ls = remote["ls"]
    >>> with remote.cwd("/lib"):
    ...     (r_ls | grep["0.so.0"])()
    ...
    'libusb-1.0.so.0\nlibusb-1.0.so.0.0.0\n'

CLI applications
****************

.. code-block:: python

    import logging
    from plumbum import cli

    class MyCompiler(cli.Application):
        verbose = cli.Flag(["-v", "--verbose"], help = "Enable verbose mode")
        include_dirs = cli.SwitchAttr("-I", list = True, help = "Specify include directories")

        @cli.switch("--loglevel", int)
        def set_log_level(self, level):
            """Sets the log-level of the logger"""
            logging.root.setLevel(level)

        def main(self, *srcfiles):
            print("Verbose:", self.verbose)
            print("Include dirs:", self.include_dirs)
            print("Compiling:", srcfiles)

    if __name__ == "__main__":
        MyCompiler.run()

Sample output
+++++++++++++

::

    $ python3 simple_cli.py -v -I foo/bar -Ispam/eggs x.cpp y.cpp z.cpp
    Verbose: True
    Include dirs: ['foo/bar', 'spam/eggs']
    Compiling: ('x.cpp', 'y.cpp', 'z.cpp')

Colors and Styles
-----------------

.. code-block:: python

    from plumbum import colors
    with colors.red:
        print("This library provides safe, flexible color access.")
        print(colors.bold | "(and styles in general)", "are easy!")
    print("The simple 16 colors or",
          colors.orchid & colors.underline | '256 named colors,',
          colors.rgb(18, 146, 64) | "or full rgb colors",
          'can be used.')
    print("Unsafe " + colors.bg.dark_khaki + "color access" + colors.bg.reset + " is available too.")
