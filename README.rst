Plumbum: Shell Combinators
==========================

Ever wanted wrist-handiness of shell scripts, but in a modern, object-oriented language and 
a rich library? Say hello to *Plumbum Shell Combinators*. Plumbum (Latin for *lead*) is a small 
yet very functional library for writing programs a la shell scripts, but in python, of course. 
Plumbum treats programs as functions, which you can invoke to get run the program, and form
pipelines, just like shell.  

Local Commands
--------------
Plumbum exposes a special singleton object named `local`, which represents your local machine
and serves as a factory for command objects (among other tasks) ::

    >>> from plumbum import local
    >>>
    >>> ls = local["ls"]
    >>> ls
    <Command C:\Program Files\Git\bin\ls.exe>
    >>>    
    >>> ls()
    'README.rst\nplumbum\nsetup.py\ntests\ntodo.txt\n'
    >>> ls("-a")
    '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\n...\n'

With a touch of magic, you can *import* commands from the local object, like so::

    >>> from plumbum.local import grep, cat
    >>> cat
    <Command C:\Program Files\Git\bin\cat.exe>

In order to form pipelines and other chains, we must first learn to *bind arguments* to commands.
As you've seen, *invoking* commands runs the program; by using square brackets (`__getitem__`),
we can create bound commands ::

    >>> ls["-l"]
    BoundCommand(<Command C:\Program Files\Git\bin\ls.exe>, ('-l',))
    >>> grep["-v", ".py"]
    BoundCommand(<Command C:\Program Files\Git\bin\grep.exe>, ('-v', '.py'))

Forming pipelines now is easy and straight-forwards, using  bitwise-or (`|`) :: 

    >>> chain = ls["-l"] | grep[".py"]
    >>> print chain
    (C:\Program Files\Git\bin\ls.exe '-l' | C:\Program Files\Git\bin\grep.exe '.py')
    >>>
    >>> chain()
    '-rw-r--r--    1 sebulba  Administ        0 Apr 27 11:54 setup.py\n'

We can also use redirection into files (or any object that exposes a real `fileno()`). If a string
is given, it is assumed to be a file name, and a file with that name is opened for you. 
In this example, we're reading from `stdin` into `grep world`, and redirect the output to a file 
named `tmp.txt` ::
    
    >>> import sys
    >>> ((grep["world"] < sys.stdin) > "tmp.txt")()
    hello
    hello world
    what has the world become?
    foo                                    # Ctrl+D pressed
    ''                                     # This is the empty string that returns from 
                                           # the command's stdout (as it's actually redirected)

And it was indeed written to the file ::

    >>> cat("tmp.txt")
    'hello world\nwhat has the world become?\n'

If you need to send input into a program (through its `stdin`), instead of writing it to a file
and redirecting this into into `stdin`, you can use the shortcut `<<` ::

    >>> (cat << "hello world\nfoo\nbar\spam" | grep["oo"]) ()
    'foo\n'

If the command we're running fails (returns a non-zero exit code), we'll get an exception ::

    >>> cat("non/existing.file")
    Traceback (most recent call last):
      ...
    ProcessExecutionError: Command line: ['C:\\Program Files\\Git\\bin\\cat.exe', 'non/existing.file']
    Exit code: 1
    Stderr:  | "C:/Program Files/Git/bin/cat.exe": non/existing.file: No such file or directory

In order to avoid such exceptions, or when a different exit code is expected, just pass  
`retcode = xxx` as a keyword argument. If `retcode` is `None`, no exception checking is performed
(any exit code is accepted); otherwise, the exit code is expected to match the one you passed ::

    >>> cat("non/existing.file", retcode = None)
    '' 
    >>> cat("non/existing.file", retcode = 17)
    Traceback (most recent call last):
      ...
    ProcessExecutionError: Command line: ['C:\\Program Files\\Git\\bin\\cat.exe', 'non/existing.file']
    Exit code: 1
    Stderr:  | "C:/Program Files/Git/bin/cat.exe": non/existing.file: No such file or directory


Notice that calling commands (or chained-commands) only returns their `stdout`. In order to
get hold of the exit code or `stderr`, you'll need to use the `run()` method, which returns 
a 3-tuple of the exit code, `stdout`, and `stderr` ::

    >>> ls.run("-a")
    (0, '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\...', '')

And, if you want to want to execute commands in the background (i.e., not wait for them to 
finish), you can use the `popen` method, which returns a normal `subprocess.Popen` object ::

    >>> p = ls.popen("-a")
    >>> p.communicate()
    ('.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\n...', '')

In order to make programming easier, there are two special objects called `FG` and `BG`,
which you can use. `FG` runs programs in the foreground (they receive the parent's `stdin`, 
`stdout` and `stderr`), and `BG` runs programs in the background (much like `popen` above,
but it returns a `Future` object, instead of a `subprocess.Popen` one).

    >>> from plumbum import FG, BG
    >>> ls["-l"] & FG
    total 5
    -rw-r--r--    1 sebulba  Administ     4478 Apr 29 15:02 README.rst
    drwxr-xr-x    2 sebulba  Administ     4096 Apr 27 12:18 plumbum
    -rw-r--r--    1 sebulba  Administ        0 Apr 27 11:54 setup.py
    drwxr-xr-x    2 sebulba  Administ        0 Apr 27 11:54 tests
    -rw-r--r--    1 sebulba  Administ       18 Apr 27 11:54 todo.txt
    >>> 
    >>> # Note that the output of `ls` went straight to the screen. 
    ...
    >>> ls["-a"] & BG
    <Future ['C:\\Program Files\\Git\\bin\\ls.exe', '-a'] (running)>
    >>> f = _
    >>> f.ready()
    False
    >>> f.wait()
    >>> f.stdout
    '.\n..\n.git\n.gitignore\n.project\n.pydevproject\nREADME.rst\nplumbum\n...'

Paths
-----
A key feature of Plumbum is `Path` objects. 

SSH
---
TDB

Remote Commands
---------------
TDB

About
-----
The project has been inspired by `PBS <https://github.com/amoffat/pbs>`_ of Andrew Moffat,
and has borrowed some of his ideas (namely importing commands). However, I felt there was too
much magic going on in PBS, and that the syntax wasn't what I had in mind when I came to write
shell programs. I contacted Andrew, but he wanted to keep PBS this way.

Besides PBS, the main purpose of the library was to be able to control remote machines with ease,
without imposing any requirements other than SSH. It began with an idea of 
`Rotem Yaari <https://github.com/vmalloc/>`_ for a libary called `pyplatform`, which was
neglected for some time now. Plumbum attempts to revive this, and throw in some extra features
too. Ultimately, it aims to replace `subprocess.Popen` altogether.

