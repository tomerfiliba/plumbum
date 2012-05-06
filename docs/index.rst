Plumbum: Shell Combinators
==========================

Ever wished the wrist-handiness of shell scripts be put into a real language? Say hello to 
*Plumbum Shell Combinators*. Plumbum (Latin for *lead*, which was used to create pipes back 
in the day) is a small yet feature-rich library for shell script-like programs in Python. 
The motto of the library is you'd *never have to resort to shell scripts again*, and thus it
attempts to mimic the shell syntax (but only where it makes sense) while keeping it cross-platform.

Apart from shell-like syntax and nifty shortcuts, the library focuses on local and 
remote command execution, local and remote *paths*, and working directory and environment 
manipulation. But enough with the talk, let's see some code! ::

    >>> from plumbum import local, FG, BG
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
    >>>
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

There's much more Plumbum can do, so be sure to read on:

.. toctree::
   :maxdepth: 2
   
   local_commands
   local_machine
   paths
   remote_machine
   cli
   api

About
=====
The original purpose of Plumbum was to enable local and remote program execution with ease, 
assuming nothing fancier than good-old SSH. On top of this, a file-system abstraction layer
was devised, so that working with local and remote files would be seamless. 

I've toyed with this idea for some time now, but it wasn't until I had to write build scripts
for a project I've been working on that I decided I've had it with shell scripts and it's time
to make it happen. Plumbum was born from the scraps of the ``Path`` class, which I 
wrote for the aforementioned build system, and the ``SshContext`` and ``SshTunnel`` classes
that I wrote for `RPyC <http://rpyc.sf.net>`_. When I combined the two with *shell combinators*
(because shell scripts do have an edge there) the magic happened and here we are.

Credits
=======
The project has been inspired by `PBS <https://github.com/amoffat/pbs>`_ 
of `Andrew Moffat <https://github.com/amoffat>`_, 
and has borrowed some of his ideas (namely treating programs like functions and the
nice trick for importing commands). However, I felt there was too much magic going on in PBS, 
and that the syntax wasn't what I had in mind when I came to write shell-like programs. 
I contacted Andrew, but he wanted to keep PBS this way. Other than that, the two libraries 
go in different directions.

Plumbum pays tribute to `Rotem Yaari <https://github.com/vmalloc/>`_ who suggested a library 
code-named ``pyplatform`` for that very same purpose, but it had never materialized.

