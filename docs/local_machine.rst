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

You can also use it as a *context manager*, so it behaves like ``pushd``/``popd``::

    >>> with local.cwd("c:\\windows"):
    ...     print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    ...     with local.cwd("c:\\windows\\system32"):
    ...         print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    ...
    c:\windows: 105
    c:\windows\system32: 3013
    >>> print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    d:\workspace\plumbum: 9

Finally, A more explicit and thread-safe way of running a command in a different directory is using the ``.with_cwd()`` method:

    >>> ls_in_docs = local.cmd.ls.with_cwd("docs")
    >>> ls_in_docs()
    'api\nchangelog.rst\n_cheatsheet.rst\ncli.rst\ncolorlib.rst\n_color_list.html\ncolors.rst\nconf.py\nindex.rst\nlocal_commands.rst\nlocal_machine.rst\nmake.bat\nMakefile\n_news.rst\npaths.rst\nquickref.rst\nremote.rst\n_static\n_templates\ntyped_env.rst\nutils.rst\n'


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
    >>> local.python("-c", "import os;print(os.environ['FOO'])")
    Traceback (most recent call last):
       [...]
    ProcessExecutionError: Unexpected exit code: 1
    Command line: | /usr/bin/python -c "import os;print(os.environ['FOO'])"
    Stderr:       | Traceback (most recent call last):
                  |   File "<string>", line 1, in <module>
                  |   File "/usr/lib/python3.5/os.py", line 725, in __getitem__
                  |     raise KeyError(key) from None
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


For further information, see the :ref:`api docs <api-local-machine>`.
