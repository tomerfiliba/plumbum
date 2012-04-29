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

There's much more Plumbum can do, so be sure to read on...

Contents
--------

.. toctree::
   :maxdepth: 2
   
   local
   path
   remote
   about


.. comment
    Indices and tables
    ==================

    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`

