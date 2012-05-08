Local Commands
==============
Plumbum exposes a special singleton object named ``local``, which represents your local machine
and serves as a factory for command objects::

    >>> from plumbum import local
    >>>
    >>> ls = local["ls"]
    >>> ls
    <LocalCommand C:\Program Files\Git\bin\ls.exe>
    >>> notepad = local["c:\\windows\\notepad.exe"]
    >>> notepad
    <LocalCommand c:\windows\notepad.exe>

If you don't specify a full path, the program is searched for in your system's ``PATH`` (and if no
match is found, an exception is raised). Otherwise, the full path is used as given. Once you have
a ``Command`` object, you can execute it like a normal function::

    >>> ls()
    'README.rst\nplumbum\nsetup.py\ntests\ntodo.txt\n'
    >>> ls("-a")
    '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\n[...]'

With just a touch of magic, you can *import* commands from the ``local`` object, like so::

    >>> from plumbum.cmd import grep, cat
    >>> cat
    <LocalCommand C:\Program Files\Git\bin\cat.exe>

.. note::
   There's no real module named ``plumbum.cmd``; it's just a dynamically-created "module", 
   added directly into ``sys.modules``, which enabled the use of ``from plumbum.cmd import foo``.
   Trying to ``import plumbum.cmd`` is bound to fail.
   
Note that underscores (``_``) will be replaced by hyphens (``-``), if the original version
is not found. Therefore, in order to get ``apt-get``, you can import ``apt_get``, for convenience.

Pipelining
----------
In order to form pipelines and other chains, we must first learn to *bind arguments* to commands.
As you've seen, *invoking* commands runs the program; by using square brackets (``__getitem__``),
we can create bound commands::

    >>> ls["-l"]
    BoundCommand(<LocalCommand C:\Program Files\Git\bin\ls.exe>, ('-l',))
    >>> grep["-v", ".py"]
    BoundCommand(<LocalCommand C:\Program Files\Git\bin\grep.exe>, ('-v', '.py'))

Forming pipelines now is easy and straight-forwards, using ``|`` (bitwise-or):: 

    >>> chain = ls["-l"] | grep[".py"]
    >>> print chain
    C:\Program Files\Git\bin\ls.exe -l | C:\Program Files\Git\bin\grep.exe .py
    >>>
    >>> chain()
    '-rw-r--r--    1 sebulba  Administ        0 Apr 27 11:54 setup.py\n'

Output/Input Redirection
------------------------
We can also use redirection into files (or any object that exposes a real ``fileno()``). 
If a string is given, it is assumed to be a file name, and a file with that name is opened 
for you. In this example, we're reading from ``stdin`` into ``grep world``, and redirect 
the output to a file named ``tmp.txt``::
    
    >>> import sys
    >>> ((grep["world"] < sys.stdin) > "tmp.txt")()
    hello
    hello world
    what has the world become?
    foo                                    
    ''

.. note::
   Parenthesis are required here! ``grep["world"] < sys.stdin > "tmp.txt"`` would 
   result in ``False``...

Right after ``foo``, Ctrl+D was pressed, which caused ``grep`` to finish. The empty string
at the end is the command's ``stdout`` (and it's empty because it actually went to a file).
Lo and behold, the file was created::

    >>> cat("tmp.txt")
    'hello world\nwhat has the world become?\n'

If you need to send input into a program (through its ``stdin``), instead of writing the data 
to a file and redirecting this file into ``stdin``, you can use the shortcut ``<<`` (shift-left)::

    >>> (cat << "hello world\nfoo\nbar\spam" | grep["oo"]) ()
    'foo\n'

Exit Codes
----------
If the command we're running fails (returns a non-zero exit code), we'll get an exception::

    >>> cat("non/existing.file")
    Traceback (most recent call last):
      [...]
    ProcessExecutionError: Command line: ['C:\\Program Files\\Git\\bin\\cat.exe', 'non/existing.file']
    Exit code: 1
    Stderr:  | "C:/Program Files/Git/bin/cat.exe": non/existing.file: No such file or directory

In order to avoid such exceptions, or when a different exit code is expected, just pass  
``retcode = xxx`` as a keyword argument. If ``retcode`` is ``None``, no exception checking 
is performed (any exit code is accepted); otherwise, the exit code is expected to match the 
one you passed::

    >>> cat("non/existing.file", retcode = None)
    '' 
    >>> cat("non/existing.file", retcode = 17)
    Traceback (most recent call last):
      [...]
    ProcessExecutionError: Command line: ['C:\\Program Files\\Git\\bin\\cat.exe', 'non/existing.file']
    Exit code: 1
    Stderr:  | "C:/Program Files/Git/bin/cat.exe": non/existing.file: No such file or directory

Run and Popen
-------------
Notice that calling commands (or chained-commands) only returns their ``stdout``. In order to
get hold of the exit code or ``stderr``, you'll need to use the ``run()`` method, which returns 
a 3-tuple of the exit code, ``stdout``, and ``stderr``::

    >>> ls.run("-a")
    (0, '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\[...]', '')

And, if you want to want to execute commands in the background (i.e., not wait for them to 
finish), you can use the ``popen`` method, which returns a normal ``subprocess.Popen`` object::

    >>> p = ls.popen("-a")
    >>> p.communicate()
    ('.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\n[...]', '')

Background and Foreground
-------------------------
In order to make programming easier, there are two special objects called ``FG`` and ``BG``,
which are there to help you. ``FG`` runs programs in the foreground (they receive the parent's 
``stdin``, ``stdout`` and ``stderr``), and ``BG`` runs programs in the background (much like 
``popen`` above, but it returns a ``Future`` object, instead of a ``subprocess.Popen`` one). 
``FG`` is especially useful for interactive programs like editors, etc., that require a ``TTY``. 
::

    >>> from plumbum import FG, BG
    >>> ls["-l"] & FG
    total 5
    -rw-r--r--    1 sebulba  Administ     4478 Apr 29 15:02 README.rst
    drwxr-xr-x    2 sebulba  Administ     4096 Apr 27 12:18 plumbum
    -rw-r--r--    1 sebulba  Administ        0 Apr 27 11:54 setup.py
    drwxr-xr-x    2 sebulba  Administ        0 Apr 27 11:54 tests
    -rw-r--r--    1 sebulba  Administ       18 Apr 27 11:54 todo.txt
    
.. note:: 
   Note that the output of ``ls`` went straight to the screen

::

    >>> ls["-a"] & BG
    <Future ['C:\\Program Files\\Git\\bin\\ls.exe', '-a'] (running)>
    >>> f = _
    >>> f.ready()
    False
    >>> f.wait()
    >>> f.stdout
    '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\n[...]'


