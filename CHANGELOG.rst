1.1
---
* `Paramiko <http://pypi.python.org/pypi/paramiko/1.8.0>`_ integration 
  `#10 <https://github.com/tomerfiliba/plumbum/issues/10>`_
* CLI: now with built-in support for `sub-commands <http://plumbum.readthedocs.org/en/latest/cli.html#sub-commands>`_.
  See also: `#43 <https://github.com/tomerfiliba/plumbum/issues/43>`_
* The "import hack" has moved to the package's ``__init__.py``, to make it importable directly
  `#45 <https://github.com/tomerfiliba/plumbum/issues/45>`_

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
