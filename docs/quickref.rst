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

================= =====================================
Utility           Usage
================= =====================================
``PROGNAME=``     Custom program name and/or color
``VERSION=``      Custom version
``DESCRIPTION=``  Custom description (or use docstring)
``COLOR_USAGE=``  Custom color for usage statement
``COLOR_GROUPS=`` Colors of groups (dictionary)
================= =====================================

Paths
=====

=============== =============================
Idiom           Description
=============== =============================
`local.cwd`     Common way to make paths
`/` Construct   Composition of parts
`//` Construct  Grep for files
Sorting         Alphabetical
Iteration       By parts
To str          Canoncical full path
Subtraction     Relative path
`in`            Check for file in folder
=============== =============================

================================================= =========================== ==================
Method                                            Description                 Compare to Pathlib
================================================= =========================== ==================
`.up(count = 1)`                                  Go up count directories
`.walk(filter=*, dir_filter=*)`                   Traverse directories
`.name`                                           The file name
`.basename`                                       DEPRACATED
`.stem`                                           Name without extension
`.dirname`                                        Directory name
`.root`                                           The file tree root
`.drive`                                          Drive letter (Windows)
`.suffix`                                         The suffix
`.suffixes`                                       A list of suffixes
`.uid`                                            User ID
`.gid`                                            Group ID
`.as_uri(scheme=None)`                            Universal Resource ID
`.join(part, ...)`                                Put together paths (`/`)
`.list()`                                         Files in directory
`.iterdir()`                                      Fast iterator over dir
`.is_dir()`                                       If path is dir
`.isdir()`                                        DEPRACATED
`.is_file()`                                      If is file
`.isfile()`                                       DEPRACATED
`.is_symlink()`                                   If is symlink
`.islink()`                                       DEPRACATED
`.exists()`                                       If file exists
`.stat()`                                         Return OS stats
`.with_name(name)`                                Replace filename
`.with_suffix(suffix, depth=1)`                   Replace suffix
`.preferred_suffix(suffix)`                       Replace suffix if no suffix
`.glob(pattern)`                                  Search for pattern
`.delete()`                                       Delete file
`.move(dst)`                                      Move file
`.rename(newname)`                                Change the file name
`.copy(dst, override=False)`                      Copy a file
`.mkdir()`                                        Make a directory
`.open(mode="r")`                                 Open a file for reading
`.read(encoding=None)`                            Read a file to text
`.write(data, encoding=None)`                     Write to a file
`.touch()`                                        Touch a file
`.chown(owner=None, group=None, recursive=None)`  Change owner
`.chmod(mode)`                                    Change permissions
`.access(mode = 0)`                               Check access permissions
`.link(dst)`                                      Make a hard link
`.symlink(dst)`                                   Make a symlink
`.unlink()`                                       Unlink a file (delete)
`.split()`                                        Split into directories
`.parts`                                          Tuple of `split`
`.relative_to(source)`                            Relative path (`-`)
================================================= =========================== ==================
