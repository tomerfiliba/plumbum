
.. _guide-paths:

Paths
=====

Apart from commands, Plumbum provides an easy to use path class that represents file system paths.
Paths are returned from several plumbum commands, and local paths can be directly created
by :func:`local.path() <platform.local_machine.LocalMachine.path>`. Paths are always absolute and
are immutable, may refer to a remote machine, and can be used like a ``str``.
In many respects, paths provide a similar API to pathlib in the Python 3.4+ standard library,
with a few improvements and extra features.

.. versionadded:: 1.6

    Paths now support more pathlib like syntax, several old names have been depreciated, like ``.basename``

The primary ways to create paths are from ``.cwd``, ``.env.home``, or ``.path(...)`` on a local
or remote machine, with ``/`` or ``//`` for composition.

.. note::

    The path returned from ``.cwd`` can also be used in a context manager and has a ``.chdir(path)`` function.
    See :ref:`guide-local-machine` for an example.

Paths provide a variety of functions that allow you to check the status of a file::

    >>> p = local.path("c:\\windows")
    >>> p.exists()
    True
    >>> p.is_dir()
    True
    >>> p.is_file()
    False

Besides checking to see if a file exists, you can check the type of file using ``.is_dir()``, ``is_file()``, or ``is_symlink()``.
You can access details about the file using the properties ``.dirname``, ``.drive``, ``.root``, ``.name``, ``.suffix``,
and ``.stem`` (all suffixes). General stats can be obtained with ``.stat()``.

You can use ``.with_suffix(suffix, depth=1)`` to replace the last ``depth`` suffixes with a new suffix.
If you specify None for the depth, it will replace all suffixes (for example, ``.tar.gz`` is two suffixes).
Note that a name like ``file.name.10.15.tar.gz`` will have "5" suffixes.
Also available is ``.with_name(name)``, which will will replace the entire name.
``preferred_suffix(suffix)`` will add a suffix if one does not exist (for default suffix situations). 

Paths can be composed using ``/``::

    >>> p / "notepad.exe"
    <LocalPath c:\windows\notepad.exe>
    >>> (p / "notepad.exe").is_file()
    True
    >>> (p / "notepad.exe").with_suffix(".dll")
    <LocalPath c:\windows\notepad.dll>


You can also iterate over directories to get the contents::

    >>> for p2 in p:
    ...     print p2
    ...
    c:\windows\addins
    c:\windows\appcompat
    c:\windows\apppatch
    ...

Paths also supply ``.iterdir()``, which may be faster on Python 3.5.

Globing can be easily performed using ``//`` (floor division)::
    >>> p // "*.dll"
    [<LocalPath c:\windows\masetupcaller.dll>, ...] 
    >>> p // "*/*.dll"
    [<LocalPath c:\windows\apppatch\acgenral.dll>, ...]
    >>> local.cwd / "docs" // "*.rst"
    [<LocalPath d:\workspace\plumbum\docs\cli.rst>, ...]


.. versionadded:: 1.6 

    Globing a tuple will glob for each of the items in the tuple, and return the aggregated result.

Files can be opened and read directly::
    >>> with(open(local.cwd / "docs" / "index.rst")) as f:
    ...     print(read(f))
    <...output...>

.. versionadded:: 1.6

    Support for treating a path exactly like a ``str``, so they can be used directly in ``open()``.

Paths also supply ``.delete()``, ``.copy(destination, override=False)``, and ``.move(destination)``. On systems that 
support it, you can also use ``.symlink(destination)``, ``.link(destination)``, and ``.unlink()``. You can change permissions with ``.chmod(mode)``,
and change owners with ``.chown(owner=None, group=None, recursive=None)``. If ``recursive`` is ``None``, this will be recursive only
if the path is a directory.

For **copy**, **move**, or **delete**
in a more general helper function form, see the :ref:`utils modules <guide-utils>`.

Relative paths can be computed using ``.relative_to(source)`` or ``mypath - basepath``, though it should be noted
that relative paths are not as powerful as absolute paths, and are primarily for recording a path or printing.

For further information, see the :ref:`api docs <api-path>`.
