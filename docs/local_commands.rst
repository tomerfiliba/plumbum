.. _guide-local-commands:

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
match is found, a ``CommandNotFound`` exception is raised). Otherwise, the full path is used as given.
Once you have a ``Command`` object, you can execute it like a normal function::

    >>> ls()
    'README.rst\nplumbum\nsetup.py\ntests\ntodo.txt\n'
    >>> ls("-a")
    '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\n[...]'

.. _fallbacks:

If you use the ``.get()`` method instead of ``[]``, you can include fallbacks to try if the
first command does not exist on the machine. This can be used to get one of several
equivalent commands, or it can be used to check for common locations of a command if
not in the path. For example::

    pandoc = local.get('pandoc',
                       '~/AppData/Local/Pandoc/pandoc.exe',
                       '/Program Files/Pandoc/pandoc.exe',
                       '/Program Files (x86)/Pandoc/pandoc.exe')

An exception is still raised if none of the commands are found. Unlike ``[]`` access,
an exception will be raised if the executable does not exist.

.. versionadded:: 1.6

    The ``.get`` method

.. _import-hack:

With just a touch of magic, you can *import* commands from the mock module ``cmd``, like so::

    >>> from plumbum.cmd import grep, cat
    >>> cat
    <LocalCommand C:\Program Files\Git\bin\cat.exe>

.. note::
   There's no real module named ``plumbum.cmd``; it's a dynamically-created "module", injected 
   into ``sys.modules`` to enable the use of ``from plumbum.cmd import foo``. As of version 1.1,
   you can actually ``import plumbum.cmd``, for consistency, but it's not recommended.
   
   It is important to stress that ``from plumbum.cmd import foo`` translates to ``local["foo"]``
   behind the scenes.

If underscores (``_``) appear in the name, and the name cannot be found in the path as-is, 
the underscores will be replaced by hyphens (``-``) and the name will be looked up again.
This allows you to import ``apt_get`` for ``apt-get``.

.. _guide-local-commands-pipelining:

Pipelining
----------
In order to form pipelines and other chains, we must first learn to *bind arguments* to commands.
As you've seen, *invoking* a command runs the program; by using square brackets (``__getitem__``),
we can create bound commands::

    >>> ls["-l"]
    BoundCommand(<LocalCommand C:\Program Files\Git\bin\ls.exe>, ('-l',))
    >>> grep["-v", ".py"]
    BoundCommand(<LocalCommand C:\Program Files\Git\bin\grep.exe>, ('-v', '.py'))

You can think of bound commands as commands that "remember" their arguments. Creating a bound
command does not run the program; in order to run it, you'll need to call (invoke) it,
like so: ``ls["-l"]()`` (in fact, ``ls["-l"]()`` is equivalent to ``ls("-l")``).

Now that we can bind arguments to commands, forming pipelines is easy and straight-forwards, 
using ``|`` (bitwise-or):: 

    >>> chain = ls["-l"] | grep[".py"]
    >>> print chain
    C:\Program Files\Git\bin\ls.exe -l | C:\Program Files\Git\bin\grep.exe .py
    >>>
    >>> chain()
    '-rw-r--r--    1 sebulba  Administ        0 Apr 27 11:54 setup.py\n'

.. _guide-local-commands-redir:

Input/Output Redirection
------------------------
We can also use redirection into files (or any object that exposes a real ``fileno()``). 
If a string is given, it is assumed to be a file name, and a file with that name is opened 
for you. In this example, we're reading from ``stdin`` into ``grep world``, and redirecting
the output to a file named ``tmp.txt``::
    
    >>> import sys
    >>> ((grep["world"] < sys.stdin) > "tmp.txt")()
    hello
    hello world
    what has the world become?
    foo                                    # Ctrl+D pressed
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

.. note::
   If you wish to accept several valid exit codes, ``retcode`` may be a tuple or a list. 
   For instance, ``grep("foo", "myfile.txt", retcode = (0, 2))``   
   
   If you need to have both the output/error and the exit code (using exceptions would provide either 
   but not both), you can use the `run` method, which will provide all of them
   
   >>>  cat["non/existing.file"].run(retcode=None)
   (1, u'', u'/bin/cat: non/existing.file: No such file or directory\n')

   


If you need the value of the exit code, there are two ways to do it. You can call ``.run(retcode=None)``
(or any other valid retcode value) on a command, you will get a tuple ``(retcode, stdin, stdout)`` (see
`Run and Popen`_. If you just need the recode, or want to check the retcode, there are two special
objects that can be applied to your command to run it and get or test the retcode. For example::

    >>> cat["non/existing.file"] & RETCODE
    1
    >>> cat["non/existing.file"] & TF
    False
    >>> cat["non/existing.file"] & TF(1)
    True

.. note::
   If you want to run these commands in the foreground (see `Background and Foreground`_), you can give
   ``FG=True`` to ``TF`` or ``RETCODE``.
   For instance, ``cat["non/existing.file"] & TF(1,FG=True)``

.. versionadded:: 1.5

    The ``TF`` and ``RETCODE`` modifiers

Run and Popen
-------------
Notice that calling commands (or chained-commands) only returns their ``stdout``. In order to
get hold of the exit code or ``stderr``, you'll need to use the ``run()`` method, which returns 
a 3-tuple of the exit code, ``stdout``, and ``stderr``::

    >>> ls.run("-a")
    (0, '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\[...]', '')

You can also pass ``retcode`` as a keyword argument to ``run`` in the same way discussed above. 

And, if you want to want to execute commands "in the background" (i.e., not wait for them to 
finish), you can use the ``popen`` method, which returns a normal ``subprocess.Popen`` object::

    >>> p = ls.popen("-a")
    >>> p.communicate()
    ('.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\n[...]', '')

You can read from its ``stdout``, ``wait()`` for it, ``terminate()`` it, etc.

.. _guide-local-commands-bgfg:

Background and Foreground
-------------------------
In order to make programming easier, there are two special objects called ``FG`` and ``BG``,
which are there to help you. ``FG`` runs programs in the foreground (they receive the parent's 
``stdin``, ``stdout`` and ``stderr``), and ``BG`` runs programs in the background (much like 
``popen`` above, but it returns a ``Future`` object, instead of a ``subprocess.Popen`` one). 
``FG`` is especially useful for interactive programs like editors, etc., that require a ``TTY``
or input from the user. :: 

    >>> from plumbum import FG, BG
    >>> ls["-l"] & FG
    total 5
    -rw-r--r--    1 sebulba  Administ     4478 Apr 29 15:02 README.rst
    drwxr-xr-x    2 sebulba  Administ     4096 Apr 27 12:18 plumbum
    -rw-r--r--    1 sebulba  Administ        0 Apr 27 11:54 setup.py
    drwxr-xr-x    2 sebulba  Administ        0 Apr 27 11:54 tests
    -rw-r--r--    1 sebulba  Administ       18 Apr 27 11:54 todo.txt
    
.. note:: 
   The output of ``ls`` went straight to the screen

::

    >>> ls["-a"] & BG
    <Future ['C:\\Program Files\\Git\\bin\\ls.exe', '-a'] (running)>
    >>> f = _
    >>> f.ready()
    False
    >>> f.wait()
    >>> f.stdout
    '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\n[...]'


You can also start a long running process and detach it in ``nohup`` mode using the ``NOHUP`` modifier::

    >>> ls["-a"] & NOHUP

If you want to redirect the input or output to something other than ``nohup.out``, you can add parameters to the modifier::

    >>> ls["-a"] & NOHUP(stdout='/dev/null') # Or None

.. versionadded:: 1.6

    The ``NOHUP`` modifier

.. _guide-local-commands-nesting:
    
Command Nesting
---------------
The arguments of commands can be strings (or any object that can meaningfully-convert to a string), 
as we've seen above, but they can also be other **commands**! This allows nesting commands into
one another, forming complex command objects. The classic example is ``sudo``::

    >>> from plumbum.cmd import sudo
    >>> print sudo[ls["-l", "-a"]]
    /usr/bin/sudo /bin/ls -l -a
    
    >>> sudo[ls["-l", "-a"]]()
    u'total 22\ndrwxr-xr-x    8 sebulba  Administ     4096 May  9 20:46 .\n[...]'

In fact, you can nest even command-chains (i.e., pipes and redirections), e.g., 
``sudo[ls | grep["\\.py"]]``; however, that would require that the top-level program be able 
to handle these shell operators, and this is not the case for ``sudo``. ``sudo`` expects its 
argument to be an executable program, and it would complain about ``|`` not being one. 
So, there's a inherent differnce between between ``sudo[ls | grep["\\.py"]]``
and ``sudo[ls] | grep["\\.py"]`` (where the pipe is unnested) -- the first would fail, 
the latter would work as expected.

Some programs (mostly shells) will be able to handle pipes and redirections -- an example of
such a program is ``ssh``. For instance, you could run ``ssh["somehost", ls | grep["\\.py"]]()``;
here, both ``ls`` and ``grep`` would run on ``somehost``, and only the filtered output would be
sent (over SSH) to our machine. On the other hand, an invocation such as
``(ssh["somehost", ls] | grep["\\.py"])()`` would run ``ls`` on ``somehost``, send its entire
output to our machine, and ``grep`` would filter it locally. 

We'll learn more about remote command execution :ref:`later <guide-remote-commands>`. In the 
meanwhile, we should learn that command nesting works by *shell-quoting* (or *shell-escaping*) 
the nested command. Quoting normally takes place from the second level of nesting::

    >>> print ssh["somehost", ssh["anotherhost", ls | grep["\\.py"]]]
    /bin/ssh somehost /bin/ssh anotherhost /bin/ls '|' /bin/grep "'\\.py'"

In this example, we first ssh to ``somehost``, from it we ssh to ``anotherhost``, and on that host
we run the command chain. As you can see, ``|`` and the backslashes have been quoted, to prevent 
them from executing on the first-level shell; this way, they would safey get to the 
second-level shell.

For further information, see the :ref:`api docs <api-commands>`.
