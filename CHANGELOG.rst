1.6.3
-----
* Python 3.6 is now supported, critical bug fixed  (`#302 <https://github.com/tomerfiliba/plumbum/issues/302>`)
* Commands: Better handling of return codes for pipelines (`#288 <https://github.com/tomerfiliba/plumbum/pull/288>`_)
* Paths: Return split support (regression) (`#286 <https://github.com/tomerfiliba/plumbum/issues/286>`) - also supports dummy args for better ``str`` compatibility
* Paths: Added support for Python 3.6 path protocol
* Paths: Support Python's ``in`` syntax
* CLI: Added Config parser (provisional) (`#304 <https://github.com/tomerfiliba/plumbum/pull/304>`)
* Color: image plots with `python -m plumbum.cli.image` (`#304 <https://github.com/tomerfiliba/plumbum/pull/304>`)
* SSH: No longer hangs for ``timeout`` seconds on failure (`#306 <https://github.com/tomerfiliba/plumbum/issues/306>`)
* Test improvements, especially on non-linux systems

1.6.2
-----
* CLI: ``Progress`` now has a clear keyword that hides the bar on completion
* CLI: ``Progress`` without clear now starts on next line without having to manually add ``\n``.
* Commands: modifiers now accept a timeout parameter (`#281 <https://github.com/tomerfiliba/plumbum/pull/281>`_)
* Commands: ``BG`` modifier now allows ``stdout``/``stderr`` redirection (to screen, for example) (`#258 <https://github.com/tomerfiliba/plumbum/pull/258>`_)
* Commands: Modifiers no longer crash on repr (see `#262 <https://github.com/tomerfiliba/plumbum/issues/262>`_)
* Remote: ``nohup`` works again, typo fixed (`#261 <https://github.com/tomerfiliba/plumbum/issues/261>`_)
* Added better support for SunOS and other OS's. (`#260 <https://github.com/tomerfiliba/plumbum/pull/260>`_)
* Colors: Context manager flushes stream now, provides more consistent results
* Other smaller bugfixes, better support for Python 3.6+

1.6.1
-----

* CLI: ``Application`` subclasses can now be run directly, instead of calling ``.run()``, to facilitate using as entry points (`#237 <https://github.com/tomerfiliba/plumbum/pull/237>`_)
* CLI: ``gui_open`` added to allow easy opening of paths in default gui editor (`#239 <https://github.com/tomerfiliba/plumbum/pull/239>`_)
* CLI: More control over help message (`#233 <https://github.com/tomerfiliba/plumbum/pull/233>`_)
* Remote: ``cwd`` is now stashed to reduce network usage (similar to Plumbum <1.6 behavior), and absolute paths are faster, (`#238 <https://github.com/tomerfiliba/plumbum/pull/238>`_)
* Bugfix: Pipelined return codes now give correct attribution (`#243 <https://github.com/tomerfiliba/plumbum/pull/243>`_)
* Bugfix: ``Progress`` works on Python 2.6 (`#230 <https://github.com/tomerfiliba/plumbum/issues/230>`_)
* Bugfix: Colors now work with more terminals (`#231 <https://github.com/tomerfiliba/plumbum/issues/231>`_)
* Bugfix: Getting an executable no longer returns a directory  (`#234 <https://ithub.com/tomerfiliba/plumbum/issues/234>`_)
* Bugfix: Iterdir now works on Python <3.5
* Testing is now expanded and fully written in Pytest, with coverage reporting.
* Added support for Conda ( as of 1.6.2, use the `-c conda-forge` channel)

1.6.0
-----
* Added support for Python 3.5, PyPy, and better Windows and Mac support, with CI testing (`#218 <https://github.com/tomerfiliba/plumbum/pull/218>`_, `#217 <https://github.com/tomerfiliba/plumbum/pull/217>`_, `#226 <https://github.com/tomerfiliba/plumbum/pull/226>`_)
* Colors: Added colors module, support for colors added to cli (`#213 <https://github.com/tomerfiliba/plumbum/pull/213>`_)
* Machines: Added ``.get()`` method for checking several commands. (`#205 <https://github.com/tomerfiliba/plumbum/pull/205>`_)
* Machines: ``local.cwd`` now is the current directory even if you change the directory with non-Plumbum methods (fixes unexpected behavior). (`#207 <https://github.com/tomerfiliba/plumbum/pull/207>`_) 
* SSHMachine: Better error message for SSH (`#211 <https://github.com/tomerfiliba/plumbum/pull/211>`_)
* SSHMachine: Support for FreeBSD remote (`#220 <https://github.com/tomerfiliba/plumbum/pull/220>`_)
* Paths: Now a subclass of ``str``, can be opened directly (`#228 <https://github.com/tomerfiliba/plumbum/pull/228>`_)
* Paths: Improved pathlib compatibility with several additions and renames (`#223 <https://github.com/tomerfiliba/plumbum/pull/223>`_)
* Paths: Added globbing multiple patterns at once  (`#221 <https://github.com/tomerfiliba/plumbum/pull/221>`_)
* Commands: added ``NOHUP`` modifier (`#221 <https://github.com/tomerfiliba/plumbum/pull/221>`_)
* CLI: added positional argument validation (`#225 <https://github.com/tomerfiliba/plumbum/pull/225>`_)
* CLI: added ``envname``, which allows you specify an environment variable for a ``SwitchAttr`` (`#216 <https://github.com/tomerfiliba/plumbum/pull/216>`_)
* CLI terminal: added ``Progress``, a command line progress bar for iterators and ranges (`#214 <https://github.com/tomerfiliba/plumbum/pull/214>`_)
* Continued to clean out Python 2.5 hacks

1.5.0
-----
* Removed support for Python 2.5. (Travis CI does not support it anymore)
* CLI: add ``invoke``, which allows you to programmatically run applications (`#149 <https://github.com/tomerfiliba/plumbum/pull/149>`_)
* CLI: add ``--help-all`` and various cosmetic fixes: (`#125 <https://github.com/tomerfiliba/plumbum/pull/125>`_),
  (`#126 <https://github.com/tomerfiliba/plumbum/pull/126>`_), (`#127 <https://github.com/tomerfiliba/plumbum/pull/127>`_)
* CLI: add ``root_app`` property (`#141 <https://github.com/tomerfiliba/plumbum/pull/141>`_)
* Machines: ``getattr`` now raises ``AttributeError`` instead of `CommandNotFound` (`#135 <https://github.com/tomerfiliba/plumbum/pull/135>`_)
* Paramiko: ``keep_alive`` support (`#186 <https://github.com/tomerfiliba/plumbum/pull/186>`_)
* Paramiko: does not support piping explicitly now (`#160 <https://github.com/tomerfiliba/plumbum/pull/160>`_)
* Parmaiko: Added pure SFTP backend, gives STFP v4+ support (`#188 <https://github.com/tomerfiliba/plumbum/pull/188>`_)
* Paths: bugfix to ``cwd`` interaction with ``Path`` (`#142 <https://github.com/tomerfiliba/plumbum/pull/142>`_)
* Paths: read/write now accept an optional encoding parameter (`#148 <https://github.com/tomerfiliba/plumbum/pull/148>`_)
* Paths: Suffix support similar to the Python 3.4 standard library ``pathlib`` (`#198 <https://github.com/tomerfiliba/plumbum/pull/198>`_)
* Commands: renamed ``setenv`` to ``with_env`` (`#143 <https://github.com/tomerfiliba/plumbum/pull/143>`_)
* Commands: pipelines will now fail with ``ProcessExecutionError`` if the source process fails (`#145 <https://github.com/tomerfiliba/plumbum/pull/145>`_)
* Commands: added ``TF`` and ``RETCODE`` modifiers (`#202 <https://github.com/tomerfiliba/plumbum/pull/202>`_)
* Experimental concurrent machine support in ``experimental/parallel.py``
* Several minor bug fixes, including Windows and Python 3 fixes (`#199 <https://github.com/tomerfiliba/plumbum/pull/199>`_,  `#195 <https://github.com/tomerfiliba/plumbum/pull/195>`_)

1.4.2
-----
* Paramiko now supports Python 3, enabled support in Plumbum 
* Terminal: added ``prompt()``, bugfix to ``get_terminal_size()`` (`#113 <https://github.com/tomerfiliba/plumbum/pull/113>`_)
* CLI: added ``cleanup()``, which is called after ``main()`` returns
* CLI: bugfix to ``CountOf`` (`#118 <https://github.com/tomerfiliba/plumbum/pull/118>`_)
* Commands: Add a TEE modifier (`#117 <https://github.com/tomerfiliba/plumbum/pull/117>`_)
* Remote machines: bugfix to ``which``, bugfix to remote environment variables (`#122 <https://github.com/tomerfiliba/plumbum/pull/122>`_)
* Path: ``read()``/``write()`` now operate on bytes

1.4.1
-----
* Force ``/bin/sh`` to be the shell in ``SshMachine.session()`` (`#111 <https://github.com/tomerfiliba/plumbum/pull/111>`_)
* Added ``islink()`` and ``unlink()`` to path objects (`#100 <https://github.com/tomerfiliba/plumbum/pull/100>`_,
  `#103 <https://github.com/tomerfiliba/plumbum/pull/103>`_)
* Added ``access`` to path objects
* Faster ``which`` implementation (`#98 <https://github.com/tomerfiliba/plumbum/pull/98>`_)
* Several minor bug fixes

1.4
---
* Moved ``atomic`` and ``unixutils`` into the new ``fs`` package (file-system related utilities)
* Dropped ``plumbum.utils`` legacy shortcut in favor of ``plumbum.path.utils``
* Bugfix: the left-hand-side process of a pipe wasn't waited on, leading to zombies (`#89 <https://github.com/tomerfiliba/plumbum/pull/89>`_)
* Added ``RelativePath`` (the result of ``Path.relative_to``)
* Fixed more text alignment issues in ``cli.Application.help()``
* Introduced ``ask()`` and ``choose`` to ``cli.terminal``
* Bugfix: Path comparison operators were wrong
* Added connection timeout to ``RemoteMachine``

1.3
---
* ``Command.popen``: a new argument, ``new_session`` may be passed to ``Command.popen``, which runs the given 
  in a new session (``setsid`` on POSIX, ``CREATE_NEW_PROCESS_GROUP`` on Windows) 
* ``Command.Popen``: args can now also be a list (previously, it was required to be a tuple). See 
* ``local.daemonize``: run commands as full daemons (double-fork and ``setsid``) on POSIX systems, or
  detached from their controlling console and parent (on Windows).   
* ``list_processes``: return a list of running process (local/remote machines)
* ``SshMachine.nohup``: "daemonize" remote commands via ``nohup`` (not really a daemon, but good enough)
* ``atomic``: Atomic file operations (``AtomicFile``, ``AtomicCounterFile`` and ``PidFile``)
* ``copy`` and ``move``: the ``src`` argument can now be a list of files to move, e.g., ``copy(["foo", "bar"], "/usr/bin")``
* list local and remote processes
* cli: better handling of text wrapping in the generated help message
* cli: add a default ``main()`` method that checks for unknown subcommands
* terminal: initial commit (``get_terminal_size``)
* packaging: the package was split into subpackages; it grew too big for a flat namespace.
  imports are not expected to be broken by this change
* SshMachine: added ``password`` parameter, which relies on `sshpass <http://linux.die.net/man/1/sshpass>`_ to feed the 
  password to ``ssh``. This is a security risk, but it's occasionally necessary. Use this with caution!
* Commands now have a ``machine`` attribute that points to the machine they run on
* Commands gained ``setenv``, which creates a command with a bound environment
* Remote path: several fixes to ``stat`` (``StatRes``)
* cli: add lazily-loaded subcommands (e.g., ``MainApp.subcommand("foo", "my.package.foo.FooApp")``), which are imported 
  on demand
* Paths: added `relative_to and split <https://github.com/tomerfiliba/plumbum/blob/c224058bcefaf5c00fe2295389887c7ebc9d5132/tests/test_local.py#L53>`_,
  which (respectively) computes the difference between two paths and splits paths into lists of nodes
* cli: ``Predicate`` became a class decorator (it exists solely for pretty-printing anyway)
* PuttyMachine: `bugfix <https://github.com/tomerfiliba/plumbum/pull/85>`_

1.2
---
* Path: added `chmod <https://github.com/tomerfiliba/plumbum/pull/49>`_
* Path: added `link and symlink <https://github.com/tomerfiliba/plumbum/issues/65>`_
* Path: ``walk()`` now applies filter recursively (`#64 <https://github.com/tomerfiliba/plumbum/issues/64>`_)
* Commands: added `Append redirect <https://github.com/tomerfiliba/plumbum/pull/54>`_
* Commands: fix ``_subprocess`` issue (`#59 <https://github.com/tomerfiliba/plumbum/issues/59>`_)
* Commands: add ``__file__`` to module hack (`#66 <https://github.com/tomerfiliba/plumbum/issues/66>`_)  
* Paramiko: add `'username' and 'password' <https://github.com/tomerfiliba/plumbum/pull/52>`_ 
* Paramiko: add `'timeout' and 'look_for_keys' <https://github.com/tomerfiliba/plumbum/pull/67>`_
* Python 3: fix `#56 <https://github.com/tomerfiliba/plumbum/issues/56>`_ and `#55 <https://github.com/tomerfiliba/plumbum/pull/55>`_

1.1
---
* `Paramiko <http://pypi.python.org/pypi/paramiko/1.8.0>`_ integration 
  (`#10 <https://github.com/tomerfiliba/plumbum/issues/10>`_)
* CLI: now with built-in support for `sub-commands <https://plumbum.readthedocs.io/en/latest/cli.html#sub-commands>`_.
  See also: `#43 <https://github.com/tomerfiliba/plumbum/issues/43>`_
* The "import hack" has moved to the package's ``__init__.py``, to make it importable directly
  (`#45 <https://github.com/tomerfiliba/plumbum/issues/45>`_)
* Paths now support ``chmod`` (on POSIX platform) (`#49 <https://github.com/tomerfiliba/plumbum/pull/49>`_)
* The argument name of a ``SwitchAttr`` can now be given to it (defaults to ``VALUE``) 
  (`#46 <https://github.com/tomerfiliba/plumbum/pull/46>`_)

1.0.1
-----
* Windows: path are no longer converted to lower-case, but ``__eq__`` and ``__hash__`` operate on
  the lower-cased result (`#38 <https://github.com/tomerfiliba/plumbum/issues/38>`_)
* Properly handle empty strings in the argument list (`#41 <https://github.com/tomerfiliba/plumbum/issues/41>`_)
* Relaxed type-checking of ``LocalPath`` and ``RemotePath`` (`#35 <https://github.com/tomerfiliba/plumbum/issues/35>`_)
* Added ``PuttyMachine`` for Windows users that relies on ``plink`` and ``pscp`` 
  (instead of ``ssh`` and ``scp``) `(#37 <https://github.com/tomerfiliba/plumbum/issues/37>`_)

1.0.0
-----
* Rename ``cli.CountingAttr`` to ``cli.CountOf``
* Moved to `Travis <http://travis-ci.org/#!/tomerfiliba/plumbum>`_ continuous integration
* Added ``unixutils``
* Added ``chown`` and ``uid``/``gid``
* Lots of fixes and updates to the doc
* Full list of `issues <https://github.com/tomerfiliba/plumbum/issues?labels=V1.0&page=1&state=closed>`_

0.9.0
-----
Initial release
