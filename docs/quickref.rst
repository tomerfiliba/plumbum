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

================= =========================
Utility           Usage
================= =========================
``PROGNAME=``     Custom program name and/or color
``VERSION=``      Custom version
``DESCRIPTION=``  Custom description (or use docstring)
``COLOR_USAGE=``  Custom color for usage statement
``COLOR_GROUPS=`` Colors of groups (dictionary)
================= =========================

