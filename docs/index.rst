.. raw:: html

    <div style="float:right; margin:1em; padding: 1em 2em 1em 2em; background-color: #efefef;
        border-radius: 5px; border-width: thin; border-style: dotted; border-color: #0C3762;">
    <strong>Quick Links</strong><br/>
    <ul>
    <li><a href="#requirements" title="Jump to download">Download</a></li>
    <li><a href="#user-guide" title="Jump to user guide">User Guide</a></li>
    <li><a href="#api-reference" title="Jump to API reference">API Reference</a></li>
    <li><a href="#about" title="Jump to user guide">About</a></li>
    </ul>
    <hr/>
    <a href="http://tomerfiliba.com">
    <img style="display: block; margin-left: auto; margin-right: auto" 
    src="_static/fish-text-black.png" title="Tomer's Blog"/></a>
    </div>

Plumbum: Shell Combinators and More
===================================

Ever wished the wrist-handiness of shell scripts be put into a **real** programming language? 
Say hello to *Plumbum Shell Combinators*. Plumbum (Latin for *lead*, which was used to create 
pipes back in the day) is a small yet feature-rich library for shell script-like programs in Python. 
The motto of the library is **"Never write shell scripts again"**, and thus it attempts to mimic 
the **shell syntax** (*shell combinators*) where it makes sense, while keeping it all **pythonic 
and cross-platform**.

Apart from :ref:`shell-like syntax <guide-local-commands>` and :ref:`handy shortcuts <guide-utils>`, 
the library provides local and :ref:`remote <guide-remote-commands>` command execution (over SSH), 
local and remote file-system :ref:`paths <guide-paths>`, easy working-directory and 
environment :ref:`manipulation <guide-local-machine>`, and a programmatic 
:ref:`guide-cli` application toolkit. Now let's see some code!

News
====
* **2012.07.16**: Version 0.9.5 released

* **2012.05.28**: Plumbum is now `all green <http://travis-ci.org/#!/tomerfiliba/plumbum/builds/1459486>`_
  on *Travis CI*

Cheat Sheet
===========

**Basics** ::

    >>> from plumbum import local
    >>> ls = local["ls"]
    >>> ls
    LocalCommand(<LocalPath /bin/ls>)
    >>> ls()
    u'build.py\ndist\ndocs\nLICENSE\nplumbum\nREADME.rst\nsetup.py\ntests\ntodo.txt\n'
    >>> notepad = local["c:\\windows\\notepad.exe"]
    >>> notepad()                                   # Notepad window pops up
    u''

Instead of the writing ``xxx = local["xxx"]`` for every program you wish to use, you can 
also :ref:`import commands <import-hack>`:
    
    >>> from plumbum.cmd import grep, wc, cat, head
    >>> grep
    LocalCommand(<LocalPath /bin/grep>)

**Piping** ::
    
    >>> chain = ls["-a"] | grep["-v", "\\.py"] | wc["-l"]
    >>> print chain
    /bin/ls -a | /bin/grep -v '\.py' | /usr/bin/wc -l
    >>> chain()
    u'13\n'

**Redirection** ::

    >>> ((cat < "setup.py") | head["-n", 4])()
    u'#!/usr/bin/env python\nimport os\n\ntry:\n'
    >>> (ls["-a"] > "file.list")()
    u''
    >>> (cat["file.list"] | wc["-l"])()
    u'17\n'

**Working-directory manipulation** ::
    
    >>> local.cwd
    <Workdir /home/tomer/workspace/plumbum>
    >>> with local.cwd(local.cwd / "docs"):
    ...     chain()
    ... 
    u'15\n'
    
**Foreground and background execution** ::

    >>> from plumbum import FG, BG
    >>> (ls["-a"] | grep["\\.py"]) & FG         # The output is printed to stdout directly
    build.py
    .pydevproject
    setup.py
    >>> (ls["-a"] | grep["\\.py"]) & BG         # The process runs "in the background"
    <Future ['/bin/grep', '\\.py'] (running)>
    
**Command nesting** ::
    
    >>> from plumbum.cmd import sudo
    >>> print sudo[ifconfig["-a"]]
    /usr/bin/sudo /sbin/ifconfig -a
    >>> (sudo[ifconfig["-a"]] | grep["-i", "loop"]) & FG
    lo        Link encap:Local Loopback  
              UP LOOPBACK RUNNING  MTU:16436  Metric:1

**Remote commands (over SSH)** ::
    
    >>> from plumbum import SshMachine
    >>> remote = SshMachine("somehost", user = "john", keyfile = "/path/to/idrsa")
    >>> r_ls = remote["ls"]
    >>> with remote.cwd("/lib"):
    ...     (r_ls | grep["0.so.0"])()
    ... 
    u'libusb-1.0.so.0\nlibusb-1.0.so.0.0.0\n'


Development and Installation
============================
The library is developed on `github <https://github.com/tomerfiliba/plumbum>`_, and will happily 
accept `patches <http://help.github.com/send-pull-requests/>`_ from users. Please use the github's 
built-in `issue tracker <https://github.com/tomerfiliba/plumbum/issues>`_ to report any problem 
you encounter or to request features. The library is released under the permissive `MIT license 
<https://github.com/tomerfiliba/plumbum/blob/master/LICENSE>`_.

Requirements
------------

Plumbum supports **Python 2.5-3.2** (requires `six <http://pypi.python.org/pypi/six>`_) and has been 
tested on **Linux** and **Windows** machines. Any Unix-like machine should work fine out of the box,
but on Windows, you'll probably want to install a decent `coreutils <http://en.wikipedia.org/wiki/Coreutils>`_ 
environment and add it to your ``PATH``. I can recommend `mingw <http://mingw.org/>`_ (which comes 
bundled with `Git for Windows <http://msysgit.github.com/>`_), but `cygwin <http://www.cygwin.com/>`_ 
should work too. If you only wish to use Plumbum as a Popen-replacement to run Windows programs, 
then there's no need for the Unix tools.

Note that for remote command execution, an **openSSH-compatible** client is required (also bundled 
with *Git for Windows*), and a ``bash``-compatible shell and a coreutils environment is also 
expected on the host machine.

Download
--------

You can **download** the library from the `Python Package Index <http://pypi.python.org/pypi/plumbum#downloads>`_ 
(in a variety of formats), or ``easy-install plumbum`` / ``pip install plumbum`` directly. 

User Guide
==========
The user guide covers most of the features of Plumbum, with lots of code-snippets to get you 
swimming in no time. It introduces the concepts and "syntax" gradually, so it's recommended 
you read it in order.

.. toctree::
   :maxdepth: 2
   
   local_commands
   local_machine
   remote
   utils
   cli

API Reference
=============
The API reference (generated from the *docstrings* within the library) covers all of the 
exposed APIs of the library. Note that some "advance" features and some function parameters are 
missing from the guide, so you might want to consult with the API reference in these cases. 

.. toctree::
   :maxdepth: 2
   
   api/cli
   api/commands
   api/local_machine
   api/path
   api/remote_machine
   api/session
   api/utils

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
I contacted Andrew about these issues, but he wanted to keep PBS this way. Other than that, 
the two libraries go in different directions, where Plumbum attempts to provide a more
wholesome approach.

Plumbum also pays tribute to `Rotem Yaari <https://github.com/vmalloc/>`_ who suggested a 
library code-named ``pyplatform`` for that very same purpose, but which had never materialized.
