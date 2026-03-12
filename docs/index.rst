.. raw:: html

    <blockquote class="quicklinks-box">
    <strong>Quick Links</strong><br/>
    <ul>
    <li><a href="#requirements" title="Jump to download">Download</a></li>
    <li><a href="#user-guide" title="Jump to user guide">User Guide</a></li>
    <li><a href="#api-reference" title="Jump to API reference">API Reference</a></li>
    <li><a href="#about" title="Jump to user guide">About</a></li>
    </ul>
    <hr/>
    <a href="https://tomerfiliba.com" target="_blank">
    <img style="display: block; margin-left: auto; margin-right: auto" alt="Tomer Filiba"
    src="_static/fish-text-black.png" title="Tomer's Blog"/>
    <span style="color:transparent;position: absolute;font-size:5px;width: 0px;height: 0px;">Tomer Filiba</span></a>
    <br/>
    <a href="https://github.com/tomerfiliba/plumbum" target="_blank">
    <img style="display: block; margin-left: auto; margin-right: auto; opacity: 0.7; width: 70px;"
    src="_static/github-logo.png" title="Github Repo"/></a>
    <br/>
    <a alt="Build Status" href="https://github.com/tomerfiliba/plumbum/actions/workflows/ci.yml" target="_blank">
    <img src="https://github.com/tomerfiliba/plumbum/actions/workflows/ci.yml/badge.svg"
    style="display: block; margin-left: auto; margin-right: auto;" title="GitHub Actions CI status"></a>
    </blockquote>

Plumbum: Shell Combinators and More
===================================

Ever wished the compactness of shell scripts be put into a **real** programming language?
Say hello to *Plumbum Shell Combinators*. Plumbum (Latin for *lead*, which was used to create
pipes back in the day) is a small yet feature-rich library for shell script-like programs in Python.
The motto of the library is **"Never write shell scripts again"**, and thus it attempts to mimic
the **shell syntax** (*shell combinators*) where it makes sense, while keeping it all **Pythonic
and cross-platform**.

Apart from :ref:`shell-like syntax <guide-local-commands>` and :ref:`handy shortcuts <guide-utils>`,
the library provides local and :ref:`remote <guide-remote-commands>` command execution (over SSH),
local and remote file-system :ref:`paths <guide-paths>`, easy working-directory and
environment :ref:`manipulation <guide-local-machine>`, quick access to ANSI :ref:`colors <guide-colors>`, and a programmatic
:ref:`guide-cli` application toolkit. Now let's see some code!

News
====

.. include:: _news.rst
   :end-line: 10

:doc:`See the full news archive. <news>`


Cheat Sheet
===========

.. include:: _cheatsheet.rst

Development and Installation
============================

The library is developed on `GitHub <https://github.com/tomerfiliba/plumbum>`_, and will happily
accept `patches <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request>`_ from users. Please use the GitHub's
built-in `issue tracker <https://github.com/tomerfiliba/plumbum/issues>`_ to report any problem
you encounter or to request features. The library is released under the permissive `MIT license
<https://github.com/tomerfiliba/plumbum/blob/master/LICENSE>`_.

Requirements
------------

Plumbum supports **CPython** and **PyPy** and is continually tested on
**Linux**, **Mac**, and **Windows** machines through `GitHub Actions
<https://github.com/tomerfiliba/plumbum/actions>`_.  Any Unix-like machine
should work fine out of the box, but on Windows, you'll probably want to
install a decent `coreutils <https://en.wikipedia.org/wiki/GNU_Core_Utilities>`_
environment and add it to your ``PATH``, or use WSL(2). I can recommend `mingw
<https://www.mingw-w64.org/>`_ (which comes bundled with `Git for Windows
<https://gitforwindows.org/>`_), but `cygwin <https://cygwin.com/>`_ should
work too. If you only wish to use Plumbum as a Popen-replacement to run Windows
programs, then there's no need for the Unix tools.

Note that for remote command execution, an **openSSH-compatible** client is
required (also bundled with *Git for Windows*), and a ``bash``-compatible shell
and a coreutils environment is also expected on the host machine.

Download
--------

You can **download** the library from the `Python Package Index
<https://pypi.org/project/plumbum/>`_ (in a variety of formats), or
run ``pip install plumbum`` directly. If you use Anaconda, you can also get it
from the ``conda-forge`` channel with ``conda install -c conda-forge plumbum``.

User Guide
==========
The user guide covers most of the features of Plumbum, with lots of code-snippets to get you
swimming in no time. It introduces the concepts and "syntax" gradually, so it's recommended
you read it in order. A quick :ref:`reference guide is available <guide-quickref>`.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   local_commands
   paths
   local_machine
   async_support
   remote
   utils
   cli
   typed_env
   colors


.. toctree::
   :maxdepth: 1
   :caption: Reference

   news
   changelog
   quickref

API Reference
=============
The API reference (generated from the *docstrings* within the library) covers all of the
exposed APIs of the library. Note that some "advanced" features and some function parameters are
missing from the guide, so you might want to consult with the API reference in these cases.

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/cli
   api/commands
   api/machines
   api/path
   api/fs
   api/colors
   colorlib

.. note::

   The ``local`` object is an instance of a ``machine``.

About
=====
The original purpose of Plumbum was to enable local and remote program execution with ease,
assuming nothing fancier than good-old SSH. On top of this, a file-system abstraction layer
was devised, so that working with local and remote files would be seamless.

I've toyed with this idea for some time now, but it wasn't until I had to write build scripts
for a project I've been working on that I decided I've had it with shell scripts and it's time
to make it happen. Plumbum was born from the scraps of the ``Path`` class, which I
wrote for the aforementioned build system, and the ``SshContext`` and ``SshTunnel`` classes
that I wrote for `RPyC <https://rpyc.readthedocs.io/en/latest/>`_. When I combined the two with *shell combinators*
(because shell scripts do have an edge there) the magic happened and here we are.

Credits
=======
The project has been inspired by **PBS** (now called `sh <https://sh.readthedocs.io/en/latest/>`_)
of `Andrew Moffat <https://github.com/amoffat>`_,
and has borrowed some of his ideas (namely treating programs like functions and the
nice trick for importing commands). However, I felt there was too much magic going on in PBS,
and that the syntax wasn't what I had in mind when I came to write shell-like programs.
I contacted Andrew about these issues, but he wanted to keep PBS this way. Other than that,
the two libraries go in different directions, where Plumbum attempts to provide a more
wholesome approach.

Plumbum also pays tribute to `Rotem Yaari <https://github.com/vmalloc/>`_ who suggested a
library code-named ``pyplatform`` for that very purpose, but which had never materialized.
