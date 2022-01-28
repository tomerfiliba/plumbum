.. _guide-quickref:

Quick reference guide
---------------------

This is a cheatsheet for common tasks in Plumbum.

CLI
===

Optional arguments
******************

================ =========================
Utility          Usage
================ =========================
``Flag``         True or False descriptor
``SwitchAttr``   A value as a descriptor
``CountOf``      Counting version of ``Flag``
``@switch``      A function that runs when passed
``@autoswitch``  A switch that gets its name from the function decorated
``@validator``   A positional argument validator on main (or use Py3 attributes)
================ =========================


Validators
**********

Anything that produces a ``ValueError`` or ``TypeError``, is applied to argument. Some special ones included:

======================= =========================
Validator               Usage
======================= =========================
``Range``               A number in some range
``Set``                 A choice in a set
``ExistingFile``        A file (converts to Path)
``ExistingDirectory``   A directory
``NonexistentPath``     Not a file or directory
======================= =========================

Common options
**************

================== ============================ ==================
Option             Used in                      Usage
================== ============================ ==================
First argument     Non-auto                     The name, or list of names, includes dash(es)
Second argument    All                          The validator
docstring          ``switch``, ``Application``  The help message
``help=``          All                          The help message
``list=True``      ``switch``                   Allow multiple times (passed as list)
``requires=``      All                          A list of optional arguments to require
``excludes=``      All                          A list of optional arguments to exclude
``group=``         All                          The name of a group
``default=``       All                          The default if not given
``envname=``       ``SwitchAttr``               The name of an environment variable to check
``mandatory=True`` Switches                     Require this argument to be passed
================== ============================ ==================


Special member variables
************************

====================== =====================================
Utility                Usage
====================== =====================================
``PROGNAME=``           Custom program name and/or color
``VERSION=``            Custom version
``DESCRIPTION=``        Custom description (or use docstring)
``DESCRIPTION_MORE=``   Custom description with whitespace
``ALLOW_ABREV=True``    Allow argparse style abbreviations
``COLOR_USAGE=``        Custom color for usage statement
``COLOR_USAGE_TITLE=``  Custom color for usage statement's title
``COLOR_GROUPS=``       Colors of groups (dictionary)
``COLOR_GROUP_TITLES=`` Colors of group titles (dictionary)
====================== =====================================

Paths
=====

================= =============================
Idiom             Description
================= =============================
``local.cwd``     Common way to make paths
``/`` Construct   Composition of parts
``//`` Construct  Grep for files
Sorting           Alphabetical
Iteration         By parts
To str            Canonical full path
Subtraction       Relative path
``in``            Check for file in folder
================= =============================

..
    The main difference is the loss of relative files

=================================================== =========================== ==================
Property                                            Description                 Compare to Pathlib
=================================================== =========================== ==================
``.name``                                           The file name               ✓
``.basename``                                       DEPRECATED
``.stem``                                           Name without extension      ✓
``.dirname``                                        Directory name              ✗
``.root``                                           The file tree root          ✓
``.drive``                                          Drive letter (Windows)      ✓
``.suffix``                                         The suffix                  ✓
``.suffixes``                                       A list of suffixes          ✓
``.uid``                                            User ID                     ✗
``.gid``                                            Group ID                    ✗
``.parts``                                          Tuple of ``split``          ✓
``.parents``                                        The ancestors of the path   ✓
``.parent``                                         The ancestor of the path    ✓
=================================================== =========================== ==================

..
    Missing:
             .anchor



=================================================== =========================== ==================
Method                                              Description                 Compare to Pathlib
=================================================== =========================== ==================
``.up(count = 1)``                                  Go up count directories     ✗
``.walk(filter=*, dir_filter=*)``                   Traverse directories        ✗
``.as_uri(scheme=None)``                            Universal Resource ID       ✓
``.join(part, ...)``                                Put together paths (``/``)  ``.joinpath``
``.list()``                                         Files in directory          ✗ (shortcut)
``.iterdir()``                                      Fast iterator over dir      ✓
``.is_dir()``                                       If path is dir              ✓
``.isdir()``                                        DEPRECATED
``.is_file()``                                      If is file                  ✓
``.isfile()``                                       DEPRECATED
``.is_symlink()``                                   If is symlink               ✓
``.islink()``                                       DEPRECATED
``.exists()``                                       If file exists              ✓
``.stat()``                                         Return OS stats             ✓
``.with_name(name)``                                Replace filename            ✓
``.with_suffix(suffix, depth=1)``                   Replace suffix              ✓ (no depth)
``.preferred_suffix(suffix)``                       Replace suffix if no suffix ✗
``.glob(pattern)``                                  Search for pattern          ✓
``.split()``                                        Split into directories      ``.parts``
``.relative_to(source)``                            Relative path (``-``)       ✓
``.resolve(strict=False)``                          Does nothing                ✓
``.access(mode = 0)``                               Check access permissions    ✗
=================================================== =========================== ==================

..
    Missing:
             .match(pattern)
             .is_reserved()
             .is_absolute()
             .as_posix()
             .is_symlink()
             .is_fifo()
             .is_block_device()
             .is_char_device()
             .lchmod(mode)
             .lstat()

=================================================== =========================== ==================
Method (changes files)                              Description                 Compare to Pathlib
=================================================== =========================== ==================
``.link(dst)``                                      Make a hard link            ✗
``.symlink(dst)``                                   Make a symlink              ``.symlink_to``
``.unlink()``                                       Unlink a file (delete)      ✓
``.delete()``                                       Delete file                 ``.unlink``
``.move(dst)``                                      Move file                   ✗
``.rename(newname)``                                Change the file name        ✓
``.copy(dst, override=False)``                      Copy a file                 ✗
``.mkdir()``                                        Make a directory            ✓ (+ more args)
``.open(mode="r")``                                 Open a file for reading     ✓ (+ more args)
``.read(encoding=None)``                            Read a file to text         ``.read_text``
``.write(data, encoding=None)``                     Write to a file             ``.write_text``
``.touch()``                                        Touch a file                ✓ (+ more args)
``.chown(owner=None, group=None, recursive=None)``  Change owner                ✗
``.chmod(mode)``                                    Change permissions          ✓
=================================================== =========================== ==================

..
    Missing:
             .group()
             .owner()
             .read_bytes()
             .write_bytes()
             .replace(target)
             .rglob(pattern)
             .rmdir()
             .samefile()

Colors
======


You pick colors from ``fg`` or ``bg``, also can ``reset``

Main colors: ``black`` ``red`` ``green`` ``yellow`` ``blue`` ``magenta`` ``cyan`` ``white``

Default styles: ``warn`` ``title`` ``fatal`` ``highlight`` ``info`` ``success``

Attrs: ``bold`` ``dim`` ``underline`` ``italics`` ``reverse`` ``strikeout`` ``hidden``
