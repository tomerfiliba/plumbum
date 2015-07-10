.. _guide-local-machine:

The Local Object
================
So far we've only seen running local commands, but there's more to the ``local`` object than
this; it aims to "fully represent" the *local machine*. 

First, you should get acquainted with ``which``, which performs program name resolution in 
the system ``PATH`` and returns the first match (or raises an exception if no match is found)::

    >>> local.which("ls")
    <LocalPath C:\Program Files\Git\bin\ls.exe>
    >>> local.which("nonexistent")
    Traceback (most recent call last):
       [...]
    plumbum.commands.CommandNotFound: ('nonexistent', [...])

Another member is ``python``, which is a command object that points to the current interpreter 
(``sys.executable``)::

    >>> local.python
    <LocalCommand c:\python27\python.exe>
    >>> local.python("-c", "import sys;print sys.version")
    '2.7.2 (default, Jun 12 2011, 15:08:59) [MSC v.1500 32 bit (Intel)]\r\n'

Working Directory
-----------------
The ``local.cwd`` attribute represents the current working directory. You can change it like so::

    >>> local.cwd
    <Workdir d:\workspace\plumbum>
    >>> local.cwd.chdir("d:\\workspace\\plumbum\\docs")
    >>> local.cwd
    <Workdir d:\workspace\plumbum\docs>

But a much more useful pattern is to use it as a *context manager*, so it behaves like 
``pushd``/``popd``::

    >>> with local.cwd("c:\\windows"):
    ...     print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    ...     with local.cwd("c:\\windows\\system32"):
    ...         print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    ...
    c:\windows: 105
    c:\windows\system32: 3013
    >>> print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    d:\workspace\plumbum: 9

Environment
-----------
Much like ``cwd``, ``local.env`` represents the *local environment*. It is a dictionary-like 
object that holds **environment variables**, which you can get/set intuitively::

    >>> local.env["JAVA_HOME"]
    'C:\\Program Files\\Java\\jdk1.6.0_20'
    >>> local.env["JAVA_HOME"] = "foo"

And similarity to ``cwd`` is the context-manager nature of ``env``; each level would have
it's own private copy of the environment::

    >>> with local.env(FOO="BAR"):
    ...     local.python("-c", "import os;print os.environ['FOO']")
    ...     with local.env(FOO="SPAM"):
    ...         local.python("-c", "import os;print os.environ['FOO']")
    ...     local.python("-c", "import os;print os.environ['FOO']")
    ...
    'BAR\r\n'
    'SPAM\r\n'
    'BAR\r\n'
    >>> local.python("-c", "import os;print os.environ['FOO']")
    Traceback (most recent call last):
       [...]
    ProcessExecutionError: Command line: ['c:\\python27\\python.exe', '-c', "import os;print os.environ['FOO']"]
    Exit code: 1
    Stderr:  | Traceback (most recent call last):
             |   File "<string>", line 1, in <module>
             |   File "c:\python27\lib\os.py", line 423, in __getitem__
             |     return self.data[key.upper()]
             | KeyError: 'FOO'

In order to make cross-platform-ness easier, the ``local.env`` object provides some convenience 
properties for getting the username (``.user``), the home path (``.home``), and the executable path
(``path``) as a list. For instance::

    >>> local.env.user
    'sebulba'
    >>> local.env.home
    <Path c:\Users\sebulba>
    >>> local.env.path
    [<Path c:\python27\lib\site-packages\gtk-2.0\runtime\bin>, <Path c:\Users\sebulba\bin>, ...]
    >>>
    >>> local.which("python")
    <Path c:\python27\python.exe>
    >>> local.env.path.insert(0, "c:\\python32")
    >>> local.which("python")
    <Path c:\python32\python.exe>

.. _guide-paths:

Local Paths
===========
Apart from commands, Plumbum provides an easy to use path class that represents file system paths.
You've already seen paths; for instance, ``local.cwd`` is one, and so is the result of 
``local.which``. Paths are created by :func:`local.path() <platform.local_machine.LocalMachine.path>`,
and you can join paths using ``/`` (division), perform globbing using ``//`` (floor division), 
iterate over the files and subdirectories contained in a directory, read and write file contents, 
etc. ::

    >>> p = local.path("c:\\windows")
    >>> p.exists()
    True
    >>> p.isdir()
    True
    >>> p.isfile()
    False
    >>> p / "notepad.exe"
    <LocalPath c:\windows\notepad.exe>
    >>> (p / "notepad.exe").isfile()
    True
    >>> (p / "notepad.exe").with_suffix(".dll")
    <LocalPath c:\windows\notepad.dll>
    >>> for p2, _ in zip(p, range(3)):
    ...     print p2
    ...
    c:\windows\addins
    c:\windows\appcompat
    c:\windows\apppatch
    >>> p // "*.dll"
    [<LocalPath c:\windows\masetupcaller.dll>, ...] 
    >>> p // "*/*.dll"
    [<LocalPath c:\windows\apppatch\acgenral.dll>, ...]
    >>> local.cwd / "docs" // "*.rst"
    [<LocalPath d:\workspace\plumbum\docs\cli.rst>, ...]


If you need to **copy**, **move**, or **delete** paths, see the :ref:`utils modules <guide-utils>`



