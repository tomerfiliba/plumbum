Plumbum: Shell Combinators
==========================

Ever wished the wrist-handiness of shell scripts be put into a real language? Say hello to 
*Plumbum Shell Combinators*. Plumbum (Latin for *lead*, which was used to create pipes back 
in the day) is a small yet feature-rich library for shell script-like programs in Python. 
The motto of the library is you'd *never have to resort to shell scripts again*, and thus it
attempts to mimic the shell syntax (but only where it makes sense) while keeping it cross-platform.

Apart from shell-like syntax and nifty shortcuts, the library focuses on local and 
remote command execution, local and remote *paths*, and working directory and environment 
manipulation. But enough with the talk, let's see some code!

.. note::
   This is only a teaser; the full documentation can be found at 
   `Read the Docs <http://plumbum.readthedocs.org>`_

Basic Usage
-----------
::

    >>> from plumbum import local
    >>> from plumbum.local import ls, grep, cat, wc
    >>>
    >>> ls()
    'LICENSE\nREADME.rst\ndist\ndocs\nplumbum\n[...]'
    >>>
    >>> chain = ls | wc["-l"]
    >>> print chain
    (C:\Program Files\Git\bin\ls.exe | C:\Program Files\Git\bin\wc.exe '-l')
    >>> chain()
    '9\n'
    >>> notepad = local["c:\\windows\\notepad.exe"]
    >>> notepad()
    ''

Foregound and Background
------------------------
::

    >>> from plumbum import FG, BG
    >>> ls["-l"] & FG
    total 10
    -rw-r--r--    1 sebulba  Administ     1079 Apr 29 15:34 LICENSE
    -rw-r--r--    1 sebulba  Administ     1318 Apr 29 16:56 README.rst
    drwxr-xr-x    2 sebulba  Administ        0 Apr 29 16:59 dist
    drwxr-xr-x    5 sebulba  Administ     4096 Apr 29 23:38 docs
    drwxr-xr-x    2 sebulba  Administ     4096 Apr 29 16:52 plumbum
    [...]
    >>> (ls["-a"] | wc["-l"]) & BG
    <Future ['C:\\Program Files\\Git\\bin\\wc.exe', '-l'] (running)>
    >>> f=_
    >>> f.wait()
    >>> f.stdout
    '16\n'

Working Directory and Environment
---------------------------------
::

    >>> with local.cwd("c:\\windows"):
    ...     (ls | wc["-l"])()
    ...
    '105\n'
    >>>
    >>> with local.env(FOO="BAR"):
    ...     with local.env(FOO="SPAM"):
    ...         local.python("-c", "import os;print os.environ['FOO']")
    ...     local.python("-c", "import os;print os.environ['FOO']")
    ...
    'SPAM\r\n'
    'BAR\r\n'

Remote Execution (over SSH)
---------------------------
::

    >>> from plumbum import Remote
    >>> r = Remote.connect("linuxbox.foo.bar")
    >>> r["uname"]()
    'Linux\n'
    >>> r_ls = r["ls"]
    >>> r_ls
    <SshCommand ssh://linuxbox.foo.bar /bin/ls>
    >>>
    >>> with r.cwd("/"):
    ...     r_ls()
    ...
    'bin\nboot\ncdrom\ndev\netc\nhome\ninitrd.img\n[...]'

Tunneling (over SSH)
--------------------
::

    >>> r_python = r["python"]
    >>> f = (r_python["-c", "import socket;s=socket.socket();s.bind(('localhost',16666));" +
    ... "s.listen(1);s2=s.accept()[0];s2.send('great success')"] & BG
    >>> with r.sshctx.tunnel(12222, 16666) as tun:
    ...     import socket
    ...     s=socket.socket()
    ...     s.connect(("localhost",12222))
    ...     s.recv(100)
    ...
    'great success'
    >>> f.ready()
    True

