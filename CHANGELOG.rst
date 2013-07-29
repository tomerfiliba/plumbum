1.3
-----
* ``Command.popen``: a new argument, ``new_session`` may be passed to ``Command.popen``, which runs the given 
  in a new session (``setsid`` on POSIX, ``CREATE_NEW_PROCESS_GROUP`` on Windows) 
* ``Command.Popen``: args can now also be a list (previously, it was required to be a tuple). See 
* ``local.daemonize``: run commands as full daemons (double-fork and ``setsid``) on POSIX systems, or
  detached from their controlling console and parent (on Windows).   
* ``list_processes``: return a list of running process (local/remote machines)
* ``SshMachine.daemonize``: "daemonize" remote commands via ``nohup`` (not really a daemon, but good enough)
* ``atomic``: Atomic file operations (``AtomicFile``, ``AtomicCounterFile`` and ``PidFile``)
* ``copy`` and ``move``: the ``src`` argument can now be a list of files to move, e.g., ``copy(["foo", "bar"], "/usr/bin")``
* list local and remote processes
* cli: better handling of text wrapping in ``cli.Application.help``
* cli: add a default ``main()`` method that checks for unknown subcommands
* terminal: initial commit (``get_terminal_size``)
* packaging: the package was split into subpackages; it grew too big for a flat namespace.
  imports are not expected to be broken by this change

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
  `#10 <https://github.com/tomerfiliba/plumbum/issues/10>`_
* CLI: now with built-in support for `sub-commands <http://plumbum.readthedocs.org/en/latest/cli.html#sub-commands>`_.
  See also: `#43 <https://github.com/tomerfiliba/plumbum/issues/43>`_
* The "import hack" has moved to the package's ``__init__.py``, to make it importable directly
  `#45 <https://github.com/tomerfiliba/plumbum/issues/45>`_
* Paths now support ``chmod`` (on POSIX platform) `#49 <https://github.com/tomerfiliba/plumbum/pull/49>`_
* The argument name of a ``SwitchAttr`` can now be given to it (defaults to ``VALUE``) 
  `#46 <https://github.com/tomerfiliba/plumbum/pull/46>`_

1.0.1
-----
* Windows: path are no longer converted to lower-case, but ``__eq__`` and ``__hash__`` operate on
  the lower-cased result `#38 <https://github.com/tomerfiliba/plumbum/issues/38>`_
* Properly handle empty strings in the argument list `#41 <https://github.com/tomerfiliba/plumbum/issues/41>`_
* Relaxed type-checking of ``LocalPath`` and ``RemotePath`` `#35 <https://github.com/tomerfiliba/plumbum/issues/35>`_
* Added ``PuttyMachine`` for Windows users that relies on ``plink`` and ``pscp`` 
  (instead of ``ssh`` and ``scp``) `#37 <https://github.com/tomerfiliba/plumbum/issues/37>`_

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
