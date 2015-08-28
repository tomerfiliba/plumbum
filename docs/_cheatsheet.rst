
Basics
------

.. code-block:: python

    >>> from plumbum import local
    >>> ls = local["ls"]
    >>> ls
    LocalCommand(<LocalPath /bin/ls>)
    >>> ls()
    u'build.py\ndist\ndocs\nLICENSE\nplumbum\nREADME.rst\nsetup.py\ntests\ntodo.txt\n'
    >>> notepad = local["c:\\windows\\notepad.exe"]
    >>> notepad()                                   # Notepad window pops up
    u''                                             # Notepad window is closed by user, command returns

Instead of writing ``xxx = local["xxx"]`` for every program you wish to use, you can 
also :ref:`import commands <import-hack>`:
    
    >>> from plumbum.cmd import grep, wc, cat, head
    >>> grep
    LocalCommand(<LocalPath /bin/grep>)

See :ref:`guide-local-commands`.

Piping
------

.. code-block:: python
    
    >>> chain = ls["-a"] | grep["-v", "\\.py"] | wc["-l"]
    >>> print chain
    /bin/ls -a | /bin/grep -v '\.py' | /usr/bin/wc -l
    >>> chain()
    u'13\n'

See :ref:`guide-local-commands-pipelining`.

Redirection
-----------

.. code-block:: python

    >>> ((cat < "setup.py") | head["-n", 4])()
    u'#!/usr/bin/env python\nimport os\n\ntry:\n'
    >>> (ls["-a"] > "file.list")()
    u''
    >>> (cat["file.list"] | wc["-l"])()
    u'17\n'

See :ref:`guide-local-commands-redir`.

Working-directory manipulation
------------------------------

.. code-block:: python
    
    >>> local.cwd
    <Workdir /home/tomer/workspace/plumbum>
    >>> with local.cwd(local.cwd / "docs"):
    ...     chain()
    ...
    u'15\n'

See :ref:`guide-local-machine`.

Foreground and background execution
-----------------------------------

.. code-block:: python

    >>> from plumbum import FG, BG
    >>> (ls["-a"] | grep["\\.py"]) & FG         # The output is printed to stdout directly
    build.py
    .pydevproject
    setup.py
    >>> (ls["-a"] | grep["\\.py"]) & BG         # The process runs "in the background"
    <Future ['/bin/grep', '\\.py'] (running)>

See :ref:`guide-local-commands-bgfg`.


Command nesting
---------------   

.. code-block:: python

    >>> from plumbum.cmd import sudo
    >>> print sudo[ifconfig["-a"]]
    /usr/bin/sudo /sbin/ifconfig -a
    >>> (sudo[ifconfig["-a"]] | grep["-i", "loop"]) & FG
    lo        Link encap:Local Loopback  
              UP LOOPBACK RUNNING  MTU:16436  Metric:1


See :ref:`guide-local-commands-nesting`.

Remote commands (over SSH)
--------------------------

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
    u'libusb-1.0.so.0\nlibusb-1.0.so.0.0.0\n'

See :ref:`guide-remote`.


CLI applications
----------------

.. code-block:: python

    import logging
    from plumbum import cli

    class MyCompiler(cli.Application):
        verbose = cli.Flag(["-v", "--verbose"], help = "Enable verbose mode")
        include_dirs = cli.SwitchAttr("-I", list = True, help = "Specify include directories")

        @cli.switch("-loglevel", int)
        def set_log_level(self, level):
            """Sets the log-level of the logger"""
            logging.root.setLevel(level)

        def main(self, *srcfiles):
            print "Verbose:", self.verbose
            print "Include dirs:", self.include_dirs
            print "Compiling:", srcfiles

    if __name__ == "__main__":
        MyCompiler.run()

Sample output
+++++++++++++

::

    $ python simple_cli.py -v -I foo/bar -Ispam/eggs x.cpp y.cpp z.cpp
    Verbose: True
    Include dirs: ['foo/bar', 'spam/eggs']
    Compiling: ('x.cpp', 'y.cpp', 'z.cpp')

See :ref:`guide-cli`.

Colors and Styles
-----------------
.. warning::

   This module is not yet in a released version of Plumbum, so the interface
   may change. See the `discussion <https://github.com/tomerfiliba/plumbum/issues/215>`_ about the default stylesheet!

.. code-block:: python

    from plumbum import colors
    with colors.red:
        print("This library provides safe, flexible color access.")
        print(colors.bold | "(and styles in general)", "are easy!")
    print("The simple 16 colors or",
          colors.orchid & colors.underline | '256 named colors,',
          colors.rgb(18, 146, 64) | "or full rgb colors" ,
          'can be used.')
    print("Unsafe " + colors.bg.dark_khaki + "color access" + colors.bg.reset + " is available too.")

Sample output
+++++++++++++

.. raw:: html

    <div class="highlight">
    <code>
    <pre><font color="#800000">This library provides safe color access.
    Color <b>(and styles in general)</b> are easy!
    </font>The simple 16 colors, <font color="#D75FD7"><span style="text-decoration: underline;">256 named colors,</span></font> <font color="#129240">or full hex colors</font> can be used.
    Unsafe <span style="background-color: #AFAF5F">color access</span> is available too.</pre>
    </code>
    </div>

See :ref:`guide-colors`.
