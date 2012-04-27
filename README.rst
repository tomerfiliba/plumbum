Plumbum: Shell Combinators
==========================

Ever wanted to have the expressive power of shell scripts, but in a modern, object-oriented 
language with a rich library? Say hello to *Plumbum Shell Combinators*. Plumbum (Latin for *lead*)
is a small yet very functional library for writing programs a la shell scripts, but in python,
of course. ::

    >>> from plumbum import local
    >>> ls = local["ls"]
    >>> ls()
    'README.rst\nplumbum\nsetup.py\ntests\ntodo.txt\n'
    >>> ls("-l")
    'README.rst\nplumbum\nsetup.py\ntests\ntodo.txt\n'
    
    >>> grep = local["grep"]
    >>> chain = ls["-l"] | grep[".py"]
    >>> print chain
    (C:\Program Files\Git\bin\ls.exe '-l' | C:\Program Files\Git\bin\grep.exe '.py')
    >>> chain()
    '-rw-r--r--    1 sebulba  Administ        0 Apr 27 11:54 setup.py\n'
    
    >>> import sys
    >>> ((grep["world"] < sys.stdin) > "tmp.txt")()
    hello
    hello world
    what has the world become?
    foo  # Ctrl+D pressed
    ''
    >>> from plumbum.local import cat
    >>> cat("tmp.txt")
    'hello world\nwhat has the world become?\n'



The project has been inspired by `PBS <https://github.com/amoffat/pbs>`_ of Andrew Moffat,
and has borrowed some of his ideas (namely importing commands) 

