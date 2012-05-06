The Local Object
================
So far we've only seen running local commands, but there's more to the ``local`` object than
this; it provides some other useful features. First, you should get acquainted with ``python``,
which is a command object that points to the current interpreter (i.e., ``sys.executable``) ::

    >>> local.python
    <Command c:\python27\python.exe>
    >>> local.python("-c", "import sys;print sys.version")
    '2.7.2 (default, Jun 12 2011, 15:08:59) [MSC v.1500 32 bit (Intel)]\r\n'

Another useful member is ``which``, which performs program name resolution in the executible 
``PATH`` (returns the first match, or raises an exception if no match is found) ::

    >>> local.which("ls")
    <Path C:\Program Files\Git\bin\ls.exe>

Working Directory
-----------------
The ``local.cwd`` attribute represents the current working directory. You can change it like so ::

    >>> local.cwd
    <Workdir d:\workspace\plumbum>
    >>> local.cwd.chdir("d:\\workspace\\plumbum\\docs")
    >>> local.cwd
    <Workdir d:\workspace\plumbum\docs>

But a much more useful pattern is to use it as a *context manager*, so it behaves like 
``pushd``-``popd`` ::

    >>> with local.cwd("c:\\windows"):
    ...     print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    ...     with local.cwd("c:\\windows\\system32"):
    ...         print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    ...
    c:\windows:    105
    c:\windows\system32:   3013
    >>> print "%s:%s" % (local.cwd, (ls | wc["-l"])())
    d:\workspace\plumbum:      9

Environment
-----------
Similarly to ``cwd``, ``local.env`` represents the local environment. It is a dictionary-like 
object that holds the environment variables, which you can get/set intuitively ::

    >>> local.env["JAVA_HOME"]
    'C:\\Program Files\\Java\\jdk1.6.0_20'
    >>> local.env["JAVA_HOME"] = "foo"

And like ``cwd`` again, you can work with ``env`` as a context manager; each level would have
it's own private copy of the environment ::

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
properties for getting the username (``user``), the home path (``home``), and the executible path
(``path``). For instance ::

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
